#!/usr/bin/env python3
"""Conan recipe — portio 0.6.2 (CPython C 扩展，setuptools 构建).

portio 是 x86 端口 I/O 的 CPython 扩展模块：单文件 C 源 portio.c（403 行、
20 个 pio_* 入口：outb/outw/outl/outb_p/outw_p/outl_p/outsb/outsw/outsl/
inb/inw/inl/inb_p/inw_p/inl_p/insb/insw/insl/ioperm/iopl），无第三方 C 依赖
（setup.py 中 `libraries = []`）。

平台适配要点：
- **x86 专有 API**：OHOS aarch64 sysroot 里 <sys/io.h> 存在但 bits/io.h 为空，
  未适配源码以“隐式声明”方式编译通过，链接出未定义符号 outb/inb/ioperm...
  dlopen 时（musl BIND_NOW）报 `ImportError: Error relocating ...: outl_p:
  symbol not found`。patch 用架构宏选择实现：非 x86 下 18 个 I/O 入口抛
  portio.error（明确失败，不伪造 0 值），ioperm/iopl 返回 ENOSYS（保持上游
  “返回 errno”的 API 契约，示例 toggle.py 的 os.strerror 分支照常工作）。
- **构建入口**：上游 setup.py build_ext（setuptools / PEP 517 后端同源）；
  setuptools 不读三元组/Conan 包信息，编译参数全部经环境变量注入（CC/CFLAGS/
  C_INCLUDE_PATH/LDSHARED/LDFLAGS），不裸用未定义 shell 变量（R33）。构建在
  aarch64 OHOS 构建机上**原生执行**（需运行目标 python 读取 EXT_SUFFIX），
  x86 构建机不适用。
- **解释器**：conan python/3.12.9 提供 Python.h / libpython3.12；其 EXT_SUFFIX
  （.cpython-312-aarch64-linux-ohos.so）与设备 python3 一致，产物两侧通用。
- **E004（musl BIND_NOW）**：扩展模块显式 `-lpython3.12`，否则 dlopen 时
  Python C API 符号无法解析。
- **E077**：OHOS 加载未签名 .so 报 Permission denied，build() 与 package() 均用
  binary-sign-tool 自签并 chmod 755。
- **上游测试**：0.6.2 无自动化测试（无 tests/、无 pytest/unittest/ctest 注册），
  唯一上游样例是 toggle.py。build() 真实执行该样例的两条路径并做 import 探针，
  结果写入 res/upstream_test_summary.json 供 test_package 汇总上报；不把
  test_package 的用例算作上游用例。
- **包布局**：lib/python3.12/site-packages/portio.cpython-312-aarch64-linux-ohos.so

R26 不适用（无系统同名库冲突）。R38 不适用（产物为 Python 扩展模块，无 bin）。
"""

import json
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

_PY_VER = "3.12"
# conan python/3.12.9 不自带 setuptools；setuptools 是纯 Python 的 zip wheel，
# 构建期按 pinned sha256 取回（与仓库内 gpgmepy 2.0.0 配方同一固定件）。
_SETUPTOOLS_WHEEL = "setuptools-84.0.0-py3-none-any.whl"
_SETUPTOOLS_SHA256 = "51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670"
_SETUPTOOLS_URL = (
    "https://files.pythonhosted.org/packages/95/9c/"
    "c510029fc6ef33a6275cd2c5d3cecd6613dfd6aa401d57c54f1c18852ccf/"
    + _SETUPTOOLS_WHEEL
)
# 上游 0.6.2 唯一可执行样例（README“Usage example”即此文件）
_UPSTREAM_SAMPLE = "toggle.py"


class PortioConan(ConanFile):
    name = "portio"
    version = "0.6.2"
    description = ("Python low level port I/O for Linux x86 (CPython C extension); on OHOS/aarch64 the x86-only entry points fail explicitly")
    license = "GPL-2.0-or-later"
    homepage = "http://portio.inrim.it"
    url = "https://github.com/fabriziop/portio"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # Conan 2 的 package_type="library" 要求声明 shared 选项。扩展模块恒为共享
    # .so，配方内不读取 shared（产物形态不受其影响），声明仅满足校验；不用
    # "application" 是因为 CI L0k 会把 application 判为 CLI 工具并要求 commands.json
    # （本包无 bin 产物）。与 pycairo 1.29.0 配方同款处理。
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def validate(self):
        # R32：平台判定必须包含 OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "portio requires Linux/OHOS x86 or aarch64 sysroot, got %s"
                % self.settings.os)

    def requirements(self):
        self.requires("python/3.12.9")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---------------- helpers ----------------
    def _python(self):
        py = self.dependencies["python"]
        pkg = py.package_folder
        return (pkg,
                os.path.join(pkg, "bin", "python%s" % _PY_VER),
                os.path.join(pkg, "lib"),
                os.path.join(pkg, "include", "python%s" % _PY_VER))

    def _ext_suffix(self, py_bin, py_pkg):
        env = dict(os.environ)
        env["PYTHONHOME"] = py_pkg
        env["LD_LIBRARY_PATH"] = (os.path.join(py_pkg, "lib") + os.pathsep
                                  + env.get("LD_LIBRARY_PATH", ""))
        out = subprocess.check_output(
            [py_bin, "-c",
             "import sysconfig;print(sysconfig.get_config_var('EXT_SUFFIX'))"],
            env=env, text=True).strip()
        if not out:
            raise ConanException("cannot determine EXT_SUFFIX for %s" % py_bin)
        return out

    def _ensure_setuptools(self):
        """把 pinned setuptools wheel 解包到 build 目录，供 PYTHONPATH 使用。"""
        st_dir = os.path.join(self.build_folder, "setuptools")
        if os.path.isfile(os.path.join(st_dir, "setuptools", "__init__.py")):
            self.output.info("setuptools already unpacked at %s" % st_dir)
            return st_dir
        wheel_path = os.path.join(self.build_folder, _SETUPTOOLS_WHEEL)
        if not os.path.isfile(wheel_path):
            download(self, _SETUPTOOLS_URL, wheel_path,
                     sha256=_SETUPTOOLS_SHA256)
        os.makedirs(st_dir, exist_ok=True)
        import zipfile
        with zipfile.ZipFile(wheel_path) as zf:
            zf.extractall(st_dir)
        self.output.info("unpacked setuptools wheel into %s" % st_dir)
        return st_dir

    def _sign_so(self, path):
        """E077：OHOS 加载未签名 .so 报 Permission denied；签名后权限归零为 000，
        必须 chmod 755。签名工具缺失时告警（CI 沙箱将无法 dlopen）。"""
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            self.output.warning("portio: signer missing (%s); %s NOT signed"
                                % (signer, path))
            return False
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        sr = subprocess.run([signer, "sign", "-inFile", path, "-outFile", path,
                             "-selfSign", "1"],
                            capture_output=True, text=True)
        if sr.returncode != 0:
            self.output.warning("portio: sign failed for %s: %s"
                                % (path, (sr.stderr or sr.stdout or "").strip()[-500:]))
            return False
        os.chmod(path, 0o755)
        return True

    def _run_env(self, py_pkg, py_lib, st_dir):
        env = dict(os.environ)
        env["PYTHONHOME"] = py_pkg
        env["PYTHONPATH"] = st_dir + os.pathsep + env.get("PYTHONPATH", "")
        env["LD_LIBRARY_PATH"] = (py_lib + os.pathsep
                                  + env.get("LD_LIBRARY_PATH", ""))
        return env

    # ---------------- build ----------------
    def build(self):
        apply_conandata_patches(self)

        py_pkg, py_bin, py_lib, py_inc = self._python()
        st_dir = self._ensure_setuptools()

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or "/data/service/hnp/bin/clang"

        # setuptools 只认环境变量（不读三元组/Conan 包信息）：
        # C_INCLUDE_PATH 指向 conan python 头（sysconfig INCLUDEPY 在本环境
        # 解析为 //include/python3.12，不可用）；LDSHARED 显式链接 libpython
        # （E004：musl BIND_NOW 下扩展必须自带 Python C API 符号来源）。
        env = (
            'export PYTHONHOME="{py_pkg}" && '
            'export PYTHONPATH="{st}" && '
            'export LD_LIBRARY_PATH="{py_lib}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}" && '
            'export LIBRARY_PATH="{py_lib}" && '
            'export C_INCLUDE_PATH="{py_inc}" && '
            'export CFLAGS="-fPIC -O2" && '
            'export CC="{cc}" && '
            'export LDSHARED="{cc} -shared -fuse-ld=bfd -L{py_lib} -lpython{ver}" && '
            'export LDFLAGS="-fuse-ld=bfd -L{py_lib} -lpython{ver}" && '
            '"{py_bin}" setup.py build_ext --inplace'
        ).format(py_pkg=py_pkg, st=st_dir, py_lib=py_lib, py_inc=py_inc,
                 cc=cc, ver=_PY_VER, py_bin=py_bin)
        self.output.info("portio: building with %s (setuptools %s)"
                         % (py_bin, _SETUPTOOLS_WHEEL))
        self.run(env, cwd=self.source_folder)

        built = os.path.join(self.source_folder, "portio" + self._ext_suffix(py_bin, py_pkg))
        if not os.path.isfile(built):
            raise ConanException("portio: extension module not produced: %s" % built)
        if not self._sign_so(built) and str(self.settings.os) == "OHOS":
            # E077：OHOS 上未签名 .so 无法 dlopen，属硬失败；其它平台无此要求
            raise ConanException("portio: cannot sign %s (E077)" % built)
        self.output.info("portio: built %s" % os.path.basename(built))

        # 上游无自动化测试：真实执行上游样例 + import 探针，结果随包携带
        self._run_upstream_samples(py_bin, py_pkg, py_lib, st_dir)

    def _run_upstream_samples(self, py_bin, py_pkg, py_lib, st_dir):
        """真实执行上游样例 toggle.py 的两条路径，并做 import 探针。

        1) 原样执行：上游首行检查 os.getuid()，非 root 直接 "You need to be
           root! Exiting."（环境前置，不代表模块正确性）。
        2) 以 getuid 桩进入 API 路径：toggle.py 的 ioperm 分支在 aarch64 上返回
           ENOSYS，按上游代码打印 "ioperm: Function not implemented" 后 sys.exit()。
        两条都是真实进程执行；输出/退出码逐条记录，任何一条与预期不符即失败。
        """
        env = self._run_env(py_pkg, py_lib, st_dir)
        cwd = self.source_folder
        runs = []

        def _run(name, argv, expect_any):
            # expect_any：任一命中即算符合预期（toggle.py 的输出取决于运行者
            # 是否 root：非 root 走 root 前置检查，root 走 ioperm 分支）
            if isinstance(expect_any, str):
                expect_any = (expect_any,)
            proc = subprocess.run(argv, cwd=cwd, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=120)
            out = (proc.stdout or "").strip()
            ok = (proc.returncode == 0
                  and any(e in out for e in expect_any))
            runs.append({
                "name": name,
                "command": " ".join(argv),
                "exit_code": proc.returncode,
                "expected_any": list(expect_any),
                "output": out[-2000:],
                "result": "PASS" if ok else "FAIL",
            })
            self.output.info("upstream sample [%s] %s: rc=%d out=%r"
                             % ("PASS" if ok else "FAIL", name, proc.returncode, out[:200]))
            return ok

        probe_ok = _run(
            "import_probe",
            [py_bin, "-c", "import portio;print(portio.__file__)"],
            "portio")
        sample_ok = _run(
            "toggle.py (as-is; root check or ioperm branch)",
            [py_bin, _UPSTREAM_SAMPLE],
            ("You need to be root! Exiting.",
             "ioperm: Function not implemented"))
        api_ok = _run(
            "toggle.py (getuid stubbed to root, API path)",
            [py_bin, "-c",
             "import os,runpy;os.getuid=lambda:0;"
             "runpy.run_path(%r,run_name='__main__')" % _UPSTREAM_SAMPLE],
            "ioperm: Function not implemented")

        summary = {
            "status": "passed" if (probe_ok and sample_ok and api_ok) else "failed",
            "framework": "none",
            "command": "(upstream portio 0.6.2 ships no automated test suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "upstream_test_entry": None,
            "upstream_samples": runs,
            "upstream_sample_runs": len(runs),
            "upstream_sample_passed": sum(1 for r in runs if r["result"] == "PASS"),
            "reason": (
                "上游 0.6.2 无自动化测试入口（无 tests/ 目录、无 test_*.py、无任何"
                "测试框架注册；MANIFEST.in/Makefile 仅涉及 Sphinx 文档）。"
                "唯一上游样例 toggle.py 的两条路径与 import 探针均已真实执行，"
                "逐条结果见 upstream_samples。test_package 用例不计入上游统计。"
            ),
        }
        path = os.path.join(self.build_folder, "upstream_test_summary.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(summary, ensure_ascii=False))
        if summary["status"] != "passed":
            raise ConanException("portio: upstream sample execution failed")
        return summary

    # ---------------- package ----------------
    def package(self):
        py_pkg, py_bin, py_lib, _py_inc = self._python()
        ext = self._ext_suffix(py_bin, py_pkg)
        site = os.path.join(self.package_folder, "lib", "python%s" % _PY_VER,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        src = os.path.join(self.source_folder, "portio" + ext)
        dst = os.path.join(site, "portio" + ext)
        shutil.copy2(src, dst)
        # E077：复制后 ELF 签名失效，必须在包内重新签名
        if not self._sign_so(dst) and str(self.settings.os) == "OHOS":
            raise ConanException("portio: cannot sign packaged %s" % dst)

        # 上游样例执行结果（build() 内真实运行）随包携带，供 test_package 汇总
        summary = os.path.join(self.build_folder, "upstream_test_summary.json")
        if os.path.isfile(summary):
            res_dir = os.path.join(self.package_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            copy(self, "upstream_test_summary.json",
                 src=self.build_folder, dst=res_dir)

    def package_info(self):
        # Python 扩展模块：不提供 C/C++ 链接库
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        py_pkg, py_bin, py_lib, _py_inc = self._python()
        site = os.path.join("lib", "python%s" % _PY_VER, "site-packages")
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, site))
        # E004 双保险：运行期可解析 libpython（解释器通常已加载）
        if py_lib and os.path.isdir(py_lib):
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", py_lib)
