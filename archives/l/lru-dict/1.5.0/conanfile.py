#!/usr/bin/env python3
"""Conan recipe for lru-dict 1.5.0 — LRU dict container with a CPython C extension.

lru-dict 是「固定容量、按最近最少使用淘汰」的 dict 容器。交付形态是
**带 C 扩展的 Python 包**：`src/lru/__init__.py` 只是 4 行再导出壳，
真正的实现是 `src/lru/_lru.c`（796 行 CPython C-API 代码），
上游 `setup.py` 用 `Extension("lru._lru", ["src/lru/_lru.c"])` 编译它。
因此本包属「必须编译」的 Python 包（与仓内 lazy-object-proxy / cffi /
fastconstmap / lxml / cython 同类），不是纯 Python 直拷。

【为什么 package_type = "library" 而不是 python-require】
  conan 禁止 python-require 依赖带类型的库：
    ERROR: Package '...' with type 'python-require' cannot have a
           'static-library' dependency to 'libffi/...'
  python/3.12.9 传递带入 libffi（static-library），故本包声明
  package_type = "library" 并带 shared 选项（与 lazy-object-proxy / cffi
  / psutil 完全一致）。

【依赖】
  · python/3.12.9 —— 提供 Python.h 与 libpython3.12.so。链接期必需：产物
    的 DT_NEEDED 含 libpython3.12.so.1.0（readelf 实测）。导入时由宿主/
    conan 解释器已加载的同名 so 解析，因此**不烘焙绝对 rpath**（避免把
    构建机 cache 路径写进制品）。
  · 运行期无外部第三方依赖（pyproject.toml: dependencies = []）。

【构建方式：直接调 clang，不用 setup.py】
  上游 setup.py 等价于「把 src/lru/_lru.c 编成扩展模块」，distutils 默认
  不加 -std、直接用平台 CC。本配方按仓内 fastconstmap 先例直接调用
  OHOS SDK clang 复刻该行为，理由：
    ① 去掉对 setuptools 的构建期依赖 —— pyproject.toml 把 build 后端钉死
       为 setuptools==80.9.0，而 ohpcd 未发布该制品，按 PF4 不能写成
       tool_requires，只能构建期从平台 pip 镜像引导；直接编译可整条链路
       去掉这个网络依赖（少一个 CI 失败面）。
    ② 编译单元只有一个 .c，无需 setuptools 的 src-layout 自动发现。
  扩展名取 conan python 的 sysconfig EXT_SUFFIX（实测
  `.cpython-312-aarch64-linux-ohos.so`，与 OHOS 宿主 CPython 3.12 一致）。

【OHOS 平台适配要点：.codesign 段】
  OHOS 的 dlopen 要求被加载的 .so 带 `.codesign` 段，否则报
  `ImportError: Error loading shared library ...: Permission denied`
  （极易误导为权限问题；E077 记录该 .codesign 加载要求，
  E212 记录同一症状的另一根因 —— hmmac 安全标签）。
  **本平台实测结论**：OHOS SDK 的 clang 15.0.4
  （Target: aarch64-unknown-linux-ohos）在链接期**自动**生成 .codesign 段，
  无需手工调 binary-sign-tool。证据（见 notes.md「.codesign 实验」）：
    · 链接产物 readelf -S 直接含 `.codesign`（PROGBITS），宿主 python3
      与 conan python 均能 import；
    · 用 llvm-objcopy --remove-section .codesign 剥掉该段后，import 立即
      变为 `Permission denied` —— 证明该段确实是加载的必要条件。
  因此本配方不无条件重签（那会覆盖工具链的可信签名），而是**校验兜底**：
  打包后实测 .codesign 是否仍在；若因拷贝/替换丢失，才用 binary-sign-tool
  重签并复验；仍失败则显式报错，绝不静默交付一个装不上的模块。

【上游测试（R51）】
  上游测试入口 = `test/test_lru.py`（unittest.TestCase，26 个用例；上游
  pyproject.toml 的 [tool.cibuildwheel] test-command 为
  `python -m pytest -v`，test-sources = ["test"]）。
  本配方用 **stdlib unittest** 跑（不引入 pytest —— lru-dict 的用例是
  unittest.TestCase，unittest 即可完整收集，少一个 pip 依赖，CI 更稳）：
      <conan python> -m unittest discover -s test -p 'test_*.py' -v
  并把随包新增的鸿蒙专项用例 ohos-tests/test_ohos_lru_dict.py 一并拷入
  test/ 参加同一次 discover，使「适配后的上游测试」实际包含 ≥1 个鸿蒙用例。
  测试失败即构建失败（不做静默降级），日志落 build_folder/upstream-unittest.log。
"""
import glob
import os
import shlex
import shutil
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

PY_REF = "python/3.12.9"

# OHOS 代码签名工具（HNP 自带）——仅在 .codesign 段缺失时作为兜底使用
SIGNER = "/data/service/hnp/bin/binary-sign-tool"
OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"

UPSTREAM_TEST_TIMEOUT = 1800
SITE_REL = os.path.join("lib", "python3.12", "site-packages")


class LruDictConan(ConanFile):
    name = "lru-dict"
    version = "1.5.0"
    description = ("lru-dict — a fixed-size dict-like container that evicts "
                   "least-recently-used items (CPython C extension)")
    license = "MIT"
    homepage = "https://github.com/amitdev/lru-dict"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    # L0p：OHOS profile 需要 os/compiler/build_type/arch 四项
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)
        # 鸿蒙专项用例只有一份，放 test_package/（仓内 appdirs / plyara 的
        # 同名约定位置）。这里额外把它导进 export_sources，好让 build()
        # 也能把它并进上游 test/ 目录、与上游 26 个用例一起被 discover
        # 收集——避免同一份断言在两个地方各写一遍。
        # 注意：conan 的 copy() 会**保留 pattern 里的相对目录结构**，故落点
        # 是 export_sources_folder/test_package/（实测确认，不是扁平落点）。
        copy(self, "test_package/test_ohos_lru_dict.py",
             src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        self.requires(PY_REF)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # ---------------------------------------------------------------- helpers
    def _py_pkg(self):
        pkg = self.dependencies["python"].package_folder
        if not pkg:
            raise ConanException("python/3.12.9 package folder is unset")
        return pkg

    def _py_paths(self):
        """返回 (py_pkg, py_inc, py_lib, py_bin)。"""
        py_pkg = self._py_pkg()
        py_inc = os.path.join(py_pkg, "include", "python3.12")
        py_lib = os.path.join(py_pkg, "lib")
        py_bin = os.path.join(py_pkg, "bin", "python3.12")
        if not os.path.isfile(os.path.join(py_inc, "Python.h")):
            raise ConanException(f"Python.h missing under {py_inc}")
        if not os.path.isfile(py_bin):
            raise ConanException(f"conan python interpreter missing: {py_bin}")
        return py_pkg, py_inc, py_lib, py_bin

    def _py_env(self, py_lib, extra_pythonpath=()):
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [py_lib] + ([env["LD_LIBRARY_PATH"]] if env.get("LD_LIBRARY_PATH") else []))
        paths = [p for p in extra_pythonpath if p]
        if env.get("PYTHONPATH"):
            paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(paths)
        # 不把字节码写进源码树（保持 .orig 基线可比对）
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONNOUSERSITE"] = "1"
        return env

    def _run_py(self, py_bin, args, env, cwd, timeout=120):
        res = subprocess.run([py_bin] + list(args), cwd=cwd, env=env,
                             capture_output=True, text=True, timeout=timeout)
        return res

    def _ext_suffix(self, py_bin, py_lib):
        """取 conan python 的扩展模块后缀（EXT_SUFFIX），保证文件名被
        CPython 导入机制识别（不能凭猜写 cpython-312-...）。"""
        res = self._run_py(
            py_bin,
            ["-c", "import sysconfig;print(sysconfig.get_config_var('EXT_SUFFIX'))"],
            self._py_env(py_lib), cwd=self.build_folder)
        suffix = (res.stdout or "").strip()
        if res.returncode != 0 or not suffix.endswith(".so"):
            raise ConanException(
                "could not determine EXT_SUFFIX from the conan python "
                f"interpreter (rc={res.returncode}, out={suffix!r}, "
                f"err={(res.stderr or '').strip()[-300:]!r})")
        return suffix

    def _compiler(self):
        """编译器从 Conan conf 取（R33：不依赖未定义的 shell 环境变量）。"""
        configured = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict) or {}
        cc = configured.get("c") or shutil.which("clang")
        if not cc:
            raise ConanException(
                "C compiler not found; set tools.build:compiler_executables.c "
                "in the Conan profile")
        return cc

    @staticmethod
    def _has_codesign_section(path):
        """ELF 里是否真有 ``.codesign`` 段（纯 Python 解析段名表）。

        必须实测，不能靠签名工具的输出判定：binary-sign-tool 会打印
        "add codesign section success" 并返回 0，但产物可能不含该段
        （cffi / lazy-object-proxy 先例实测）。缺段时 dlopen 报的是极易
        误导的 ``Permission denied``（E077）。
        """
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return False
        if data[:4] != b"\x7fELF" or len(data) < 64 or data[4] != 2 or data[5] != 1:
            return False  # 非 64 位小端 ELF
        try:
            (e_shoff,) = struct.unpack_from("<Q", data, 0x28)
            e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 0x3a)
            if not e_shoff or not e_shnum:
                return False
            (strtab_off,) = struct.unpack_from(
                "<Q", data, e_shoff + e_shstrndx * e_shentsize + 0x18)
            for i in range(e_shnum):
                off = e_shoff + i * e_shentsize
                (name_off,) = struct.unpack_from("<I", data, off)
                end = data.index(b"\x00", strtab_off + name_off)
                if data[strtab_off + name_off:end] == b".codesign":
                    return True
        except (struct.error, ValueError, IndexError):
            return False
        return False

    def _ensure_codesigned(self, paths):
        """确保每个扩展模块都带 .codesign 段（OHOS dlopen 前置条件）。

        正常路径：OHOS SDK clang 已自动签名 → 仅校验，不改动（保留工具链
        的可信签名）。兜底路径：段丢失时才用 binary-sign-tool 重签并复验。
        两条路径都失败 → 显式报错（宁可不交付，也不交付装不上的模块）。
        """
        missing, repaired = [], []
        for so in paths:
            if not os.path.isfile(so):
                continue
            name = os.path.basename(so)
            if self._has_codesign_section(so):
                continue
            self.output.warning(
                f"{name} lost its .codesign section — re-signing with "
                f"{os.path.basename(SIGNER)}")
            ok = False
            if os.path.isfile(SIGNER):
                for attempt in range(1, 4):
                    tmp = so + ".signed"
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
                    if os.path.isfile(OBJCOPY):
                        self.run(f'"{OBJCOPY}" --remove-section .codesign "{so}" || true')
                    self.run(f'"{SIGNER}" sign -inFile "{so}" -outFile "{tmp}" '
                             f'-selfSign 1')
                    if os.path.isfile(tmp) and self._has_codesign_section(tmp):
                        os.replace(tmp, so)
                        os.chmod(so, 0o755)
                        if self._has_codesign_section(so):
                            ok = True
                            break
                    self.output.warning(
                        f"re-sign attempt {attempt}/3 produced no usable "
                        f".codesign section for {name}")
            if ok:
                repaired.append(name)
            else:
                missing.append(name)

        if repaired:
            self.output.info(f"re-signed: {repaired}")
        if missing:
            raise ConanException(
                "these extension modules have no .codesign section, so OHOS "
                "cannot dlopen them (the loader reports it as 'Permission "
                f"denied', which is misleading): {missing}")

    # ---------------------------------------------------------------- build
    def build(self):
        src = self.source_folder
        csrc = os.path.join(src, "src", "lru", "_lru.c")
        if not os.path.isfile(csrc):
            raise ConanException(f"upstream C source missing: {csrc}")

        _py_pkg, py_inc, py_lib, py_bin = self._py_paths()
        cc = self._compiler()
        ext_suffix = self._ext_suffix(py_bin, py_lib)
        out = os.path.join(src, "src", "lru", "_lru" + ext_suffix)

        cmd = [cc, "-shared", "-fPIC", "-O2",
               f"-I{os.path.join(src, 'src')}", f"-I{py_inc}",
               csrc, f"-L{py_lib}", "-lpython3.12",
               "-o", out]
        self.output.info("compile: " + " ".join(cmd))
        self.run(" ".join(shlex.quote(c) for c in cmd), cwd=src)

        if not os.path.isfile(out):
            raise ConanException(f"build produced no extension module: {out}")
        self.output.info(f"built extension: {os.path.basename(out)}")
        self._ensure_codesigned([out])

        self._run_upstream_tests(py_bin, py_lib)

    # ------------------------------------------------------------ upstream test
    def _run_upstream_tests(self, py_bin, py_lib):
        """跑上游 unittest 套件 + 随包新增的鸿蒙用例，并如实报告（R51）。

        失败即抛错（不做静默降级）：本包上游 26 个用例在 OHOS 上全绿，
        一旦回归必须让 conan create 直接红，而不是带着红测试交付。
        """
        test_dir = os.path.join(self.source_folder, "test")
        if not os.path.isdir(test_dir):
            raise ConanException(
                "upstream test/ not found; refusing to report a pass without "
                "running the suite (R51)")

        upstream = sorted(glob.glob(os.path.join(test_dir, "test_*.py")))
        if not upstream:
            raise ConanException(f"no upstream test modules under {test_dir}")
        self.output.info(
            "upstream test modules: "
            + ", ".join(os.path.basename(p) for p in upstream))

        # 把鸿蒙专项用例并入上游 test/ 目录，参加同一次 discover
        # （test_ohos_*.py 精确匹配：test_lru_dict.py 是消费者用例，断言模块
        #   来自 site-packages，在源码树语境下不成立，不能并进来）
        ohos_dir = os.path.join(self.export_sources_folder, "test_package")
        ohos_tests = sorted(glob.glob(os.path.join(ohos_dir, "test_ohos_*.py")))
        if not ohos_tests:
            raise ConanException(
                f"HarmonyOS test case missing under {ohos_dir} — the adapted "
                "run must include at least one OHOS case")
        for t in ohos_tests:
            shutil.copy2(t, os.path.join(test_dir, os.path.basename(t)))
        self.output.info(
            "added HarmonyOS test case(s): "
            + ", ".join(os.path.basename(p) for p in ohos_tests))

        env = self._py_env(py_lib, extra_pythonpath=[os.path.join(self.source_folder, "src")])
        cmd = [py_bin, "-m", "unittest", "discover", "-s", "test",
               "-p", "test_*.py", "-v"]
        report = os.path.join(self.build_folder, "upstream-unittest.log")
        try:
            res = subprocess.run(cmd, cwd=self.source_folder, env=env,
                                 capture_output=True, text=True,
                                 timeout=UPSTREAM_TEST_TIMEOUT)
            out = (res.stdout or "") + (res.stderr or "")
            rc = res.returncode
        except subprocess.TimeoutExpired as exc:
            out = "".join(
                (p.decode(errors="ignore") if isinstance(p, bytes) else p) or ""
                for p in (exc.stdout, exc.stderr))
            rc = -1
            self.output.warning(
                f"upstream unittest timed out after {UPSTREAM_TEST_TIMEOUT}s")

        with open(report, "w", encoding="utf-8") as fh:
            fh.write(out)
        self.output.info(f"upstream unittest rc={rc}; report: {report}")
        for line in out.strip().splitlines()[-6:]:
            self.output.info(f"unittest | {line}")

        if rc != 0:
            raise ConanException(
                f"upstream unittest failed (rc={rc}); report: {report}")
        self.output.info("upstream unittest passed")

    # ------------------------------------------------------------ package
    def package(self):
        site = os.path.join(self.package_folder, SITE_REL)
        src_pkg = os.path.join(self.source_folder, "src", "lru")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"upstream src/lru missing: {src_pkg}")

        dst_pkg = os.path.join(site, "lru")
        copy(self, "*.py", src=src_pkg, dst=dst_pkg)
        copy(self, "*.pyi", src=src_pkg, dst=dst_pkg)
        copy(self, "py.typed", src=src_pkg, dst=dst_pkg)

        sos = sorted(glob.glob(os.path.join(src_pkg, "_lru*.so")))
        if not sos:
            raise ConanException(f"built extension missing under {src_pkg}")
        for so in sos:
            copy(self, os.path.basename(so), src=src_pkg, dst=dst_pkg)

        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        if not os.path.isfile(os.path.join(dst_pkg, "__init__.py")):
            raise ConanException(f"python payload incomplete under {dst_pkg}")
        packaged = sorted(glob.glob(os.path.join(dst_pkg, "_lru*.so")))
        if not packaged:
            raise ConanException(f"extension not packaged under {dst_pkg}")
        for p in packaged:
            os.chmod(p, 0o755)
        # conan 的 copy() 可能使已有签名失效 → 打包后复验（E077），必要时重签
        self._ensure_codesigned(packaged)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = [SITE_REL]
        site = os.path.join(self.package_folder, SITE_REL)
        # 消费方与 test_package 自动获得导入路径（只 print 不声明会让消费方
        # 报 No module named lru）
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
