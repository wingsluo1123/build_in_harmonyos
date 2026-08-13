#!/usr/bin/env python3
"""test_package for boost-python 1.90.0 — 真实消费者测试。

- CMake find_package(boost_python CONFIG REQUIRED) 找到正式生成的 target
  boost_python::python312（别名 Boost::python312）；
- 编译一个真实 Boost.Python 扩展模块（导出 C++ add/greet）；
- OHOS dlopen 要求 ELF code signature：import 前对 CMake 生成的 test_ext.so 签名；
- Python 3.12 import 并断言 add(2,3)==5、add(-1,1)==0、greet() 字符串返回值；
- 同时 requires boost/1.90.0.3（传递依赖），验证两包共装无冲突。
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BoostPythonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式声明基础依赖（任务四.4：验证 boost/1.90.0.3 与 boost-python/1.90.0
        # 同时 requires 时无 BoostConfig/组件/target/include 冲突）
        self.requires("boost/1.90.0.3")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # CMakeToolchain 只在 generate() 中实例化（不在 generators 声明，避免重复）。
        # OHOS SDK 默认 ld.lld 依赖 libxml2.so.16（CI 沙箱缺失导致链接失败）；
        # 仿照 poppler 模式对三类链接统一追加 ld.bfd：
        #   - CMAKE_EXE_LINKER_FLAGS：CMake try_compile 探测可执行文件链接必需（否则
        #     探测仍调损坏的 lld 而失败）；
        #   - CMAKE_SHARED_LINKER_FLAGS / CMAKE_MODULE_LINKER_FLAGS：test_ext.so 链接。
        # 追加而非覆盖，保留已有 flags。
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            linker = self._find_ld_bfd()
            fuse = "-fuse-ld={}".format(linker)
            for flag in (
                "CMAKE_EXE_LINKER_FLAGS",
                "CMAKE_SHARED_LINKER_FLAGS",
                "CMAKE_MODULE_LINKER_FLAGS",
            ):
                old = tc.variables.get(flag, "")
                tc.variables[flag] = (str(old) + " " + fuse).strip()
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            return
        # 运行时需能找到 libc++_shared.so（OHOS SDK）
        sdk_lib = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
            "ohos/native/llvm/lib/aarch64-linux-ohos/c++"
        )
        run_dir = None
        try:
            if str(self.settings.os) == "OHOS":
                extension = self._find_extension()
                if not extension:
                    raise ConanInvalidConfiguration(
                        "test_ext.so not found after build"
                    )
                # OHOS dlopen 要求 ELF code signature：import 前签名 CMake 生成的扩展模块
                self._sign_elf_atomically(
                    extension,
                    self._find_ohos_tool("llvm-objcopy"),
                    self._find_ohos_tool("binary-sign-tool"),
                )
                # HMDFS 将 chmod 0755 映射为 0770（E046），且运行用户可能与文件
                # owner/group 不同（跨身份 EACCES）。真实运行前把产物暂存到本轮
                # TMPDIR 独立运行目录（系统 cp 创建，进程自己拥有），再从该目录
                # 动态加载 test_ext.so 与 libboost_python312.so。
                run_dir = self._stage_run_dir(extension)
                # PYTHONPATH / LD_LIBRARY_PATH 首位为运行目录（保留 conanrun 其他环境）
                os.environ["PYTHONPATH"] = (
                    run_dir + os.pathsep + os.environ.get("PYTHONPATH", "")
                )
                os.environ["LD_LIBRARY_PATH"] = (
                    run_dir
                    + os.pathsep
                    + (sdk_lib if os.path.isdir(sdk_lib) else "")
                    + os.pathsep
                    + os.environ.get("LD_LIBRARY_PATH", "")
                )
            script = os.path.join(self.source_folder, "consumer_test.py")
            self.run(
                "python3 " + script,
                cwd=run_dir or self.build_folder,
                env="conanrun",
            )
        finally:
            if run_dir and os.path.isdir(run_dir):
                # 防越界清理：只删除本轮创建、位于探测所得原生基座下且前缀为
                # boostpy-run- 的目录（容忍 /data/storage/el2/base/... 原生路径）
                real = os.path.realpath(run_dir)
                name = os.path.basename(real)
                native_bases = (
                    "/data/storage/el2/base/cache",
                    "/data/storage/el2/base/haps/entry/files",
                )
                if (
                    real
                    and name.startswith("boostpy-run-")
                    and real != "/"
                    and (
                        real.startswith(native_bases)
                        or real.startswith(
                            os.path.realpath(
                                os.environ.get("OHPC_NATIVE_TMPDIR") or ""
                            )
                        )
                    )
                ):
                    shutil.rmtree(real, ignore_errors=True)

    def _pick_native_base(self):
        """探测真实可写、可读、可执行且不属于 HMDFS 的原生运行目录基座。

        CI 进程中 conan 运行环境可能把 TMPDIR 覆盖为 $HOME/tmp（HMDFS，
        证据：CI 日志 'make: jobserver mkfifo: /storage/Users/currentUser/tmp/...'），
        而进程原生 TMPDIR（如 /data/storage/el2/base/cache）才是非 HMDFS 的
        ext2 分区。候选顺序：
          1. OHPC_NATIVE_TMPDIR 环境变量（可选显式指定）；
          2. /data/storage/el2/base/cache（nuclei 使用的 ext2 cache）；
          3. /data/storage/el2/base/haps/entry/files（argo/kubo 使用的 ext2）；
          4. 当前 TMPDIR，仅当其真实路径不属于 HMDFS（不在 /storage/Users
             下且不以 /storage/Users 开头）。
        对每个候选执行真实探针：创建任务专属子目录 → 写读探针文件 →
        chmod 0755 → 验证当前进程 R_OK/X_OK → 记录文件系统类型/拒绝原因。
        返回第一个通过的目录；若全部失败返回 ""（调用方报告 blocked）。
        """
        import tempfile as _tf

        env_tmp = os.environ.get("TMPDIR") or ""
        env_tmp_real = os.path.realpath(env_tmp) if env_tmp else ""
        hmdns_markers = ("/storage/Users",)
        candidates = []
        native_env = os.environ.get("OHPC_NATIVE_TMPDIR") or ""
        if native_env:
            candidates.append(("OHPC_NATIVE_TMPDIR", os.path.realpath(native_env)))
        candidates.append(("/data/storage/el2/base/cache", "/data/storage/el2/base/cache"))
        candidates.append(
            (
                "/data/storage/el2/base/haps/entry/files",
                "/data/storage/el2/base/haps/entry/files",
            )
        )
        if env_tmp_real and not env_tmp_real.startswith(hmdns_markers):
            candidates.append(("TMPDIR(non-HMDFS)", env_tmp_real))

        for label, cand in candidates:
            if not cand or not os.path.isdir(cand):
                self.output.warning(
                    "native-base probe %s: missing dir %r" % (label, cand)
                )
                continue
            try:
                sub = _tf.mkdtemp(prefix="boostpy-probe-", dir=cand)
            except Exception as e:
                self.output.warning(
                    "native-base probe %s: mkdtemp failed: %s" % (label, str(e)[:80])
                )
                continue
            try:
                probe_file = os.path.join(sub, "probe.txt")
                with open(probe_file, "w") as fh:
                    fh.write("ok")
                with open(probe_file) as fh:
                    content = fh.read()
                os.chmod(sub, 0o755)
                ok_perm = os.access(sub, os.R_OK) and os.access(sub, os.X_OK)
                self.output.info(
                    "native-base probe %s: write/read ok (%r), chmod 0755, "
                    "R_OK/X_OK=%s" % (label, content, ok_perm)
                )
                if content == "ok" and ok_perm:
                    return cand
                self.output.warning(
                    "native-base probe %s: probe content or perms failed" % label
                )
            finally:
                shutil.rmtree(sub, ignore_errors=True)
        return ""

    def _stage_run_dir(self, extension):
        """在原生（非 HMDFS）目录下创建本轮独立运行目录并暂存产物。

        - 通过 _pick_native_base() 探测原生基座（OHPC_NATIVE_TMPDIR →
          /data/storage/el2/base/cache → haps/entry/files → 非 HMDFS 的 TMPDIR）；
        - mkdtemp(prefix="boostpy-run-", dir=base)；
        - 结构化复制（Python 文件复制，不使用 shell 拼接 cp/rm）；
        - 复制后逐项验证：ELF magic、SHA256、.codesign、display-sign self-sign、
          os.R_OK/os.X_OK。
        """
        import tempfile

        base = self._pick_native_base()
        if not base:
            raise ConanInvalidConfiguration(
                "no writable native (non-HMDFS) staging base found; refusing to "
                "fall back to $HOME/tmp (HMDFS) for ELF dlopen staging — blocked"
            )
        run_dir = tempfile.mkdtemp(prefix="boostpy-run-", dir=base)
        pkg_lib = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder,
            "lib",
            "libboost_python312.so",
        )
        sources = {
            "test_ext.so": extension,
            "libboost_python312.so": pkg_lib,
        }
        if not os.path.isfile(pkg_lib):
            raise ConanInvalidConfiguration(
                "libboost_python312.so not found in package: " + pkg_lib
            )
        # 结构化复制（Python shutil.copyfile：只复制内容，不保留权限——不依赖
        # E046 下无效的 chmod；不使用 shell 拼接 cp/rm）
        import shutil as _shutil

        for dst, src in sources.items():
            target = os.path.join(run_dir, dst)
            _shutil.copyfile(src, target)
            # copyfile 按 umask 创建（HMDFS 映射 660 无执行位），dlopen 需要执行位：
            # best-effort chmod 0o755（HMDFS 映射 770，进程所属 group 可访问）
            os.chmod(target, 0o755)
        consumer = os.path.join(run_dir, "consumer_test.py")
        _shutil.copyfile(
            os.path.join(self.source_folder, "consumer_test.py"),
            consumer,
        )
        os.chmod(consumer, 0o644)

        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        for name in ("test_ext.so", "libboost_python312.so"):
            staged = os.path.join(run_dir, name)
            src = sources[name]
            self._verify_staged_elf(src, staged)
            if name == "libboost_python312.so":
                # 包内库责任在 package()：这里只验证，绝不重新签名。
                # 复制动作不得改变 ELF 内容（SHA256 已在 _verify_staged_elf 校验一致）。
                if not self._elf_signed_ok(staged):
                    raise ConanInvalidConfiguration(
                        "package libboost_python312.so is not validly signed "
                        "(must be signed in package()); refusing to re-sign in test"
                    )
            else:
                # test_ext.so 由 test_package 本轮构建，可在 test() 中签名
                if not self._elf_signed_ok(staged):
                    self._sign_elf_atomically(staged, objcopy, signer)
                    if not self._elf_signed_ok(staged):
                        raise ConanInvalidConfiguration(
                            "staged {name} not validly signed".format(name=name)
                        )
            # 当前进程必须对暂存文件可读且可执行（dlopen 前提）
            st = os.stat(staged)
            if not (
                os.access(staged, os.R_OK) and os.access(staged, os.X_OK)
            ):
                raise ConanInvalidConfiguration(
                    "staged {name} lacks R_OK/X_OK for the test process".format(
                        name=name
                    )
                )
        return run_dir

    def _sha256(self, path):
        import hashlib

        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _elf_signed_ok(self, path):
        """以 .codesign 段存在且 display-sign 显示 self-sign 作为签名有效判据。

        用 subprocess 捕获输出（self.run(quiet=True) 的返回值在部分 Conan
        版本不可靠），以真实工具输出为准。
        """
        if not os.path.isfile(path):
            return False
        readelf = self._find_ohos_tool("llvm-readelf")
        if not readelf:
            return False
        out = subprocess.run(
            [readelf, "-S", path], capture_output=True, text=True
        ).stdout
        if ".codesign" not in out:
            return False
        signer = self._find_ohos_tool("binary-sign-tool")
        if not signer:
            return False
        res = subprocess.run(
            [signer, "display-sign", "-inFile", path],
            capture_output=True,
            text=True,
        )
        out = (res.stdout or "") + (res.stderr or "")
        return "self-sign" in out

    def _verify_staged_elf(self, src, staged):
        """ELF magic、SHA256、.codesign 与源文件一致。"""
        if not os.path.isfile(staged):
            raise ConanInvalidConfiguration("staged missing: " + staged)
        with open(src, "rb") as f:
            src_magic = f.read(4)
        with open(staged, "rb") as f:
            staged_magic = f.read(4)
        if src_magic != b"\x7fELF" or staged_magic != b"\x7fELF":
            raise ConanInvalidConfiguration(
                "ELF magic mismatch for " + staged
            )
        if self._sha256(src) != self._sha256(staged):
            raise ConanInvalidConfiguration(
                "SHA256 mismatch after staging: " + staged
            )

    def _find_extension(self):
        matches = [
            os.path.join(self.build_folder, "test_ext.so"),
            os.path.join(self.build_folder, "test_ext.cpython-312-aarch64-linux-ohos.so"),
        ]
        for path in matches:
            if os.path.isfile(path):
                return path
        return ""

    def _find_ld_bfd(self):
        """结构化解析 OHOS ld.bfd：compiler 目录 → PATH → 标准 HNP 工具目录。

        与主配方一致；找不到时抛 ConanInvalidConfiguration，不静默回退到
        已知损坏的默认 lld（依赖 libxml2.so.16，CI 沙箱缺失）。
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, "ld.bfd") if compiler_dir else "",
            shutil.which("ld.bfd") or "",
            os.path.join("/data/service/hnp/bin", "ld.bfd"),
            "/data/service/hnp/binutils.org/binutils_2.45/bin/ld.bfd",
        ]
        for path in candidates:
            if path and os.path.isfile(path):
                return path
        raise ConanInvalidConfiguration(
            "OHOS consumer link requires ld.bfd (default SDK ld.lld depends on "
            "libxml2.so.16 which is unavailable in the CI sandbox)."
        )

    def _sign_elf_atomically(self, path, objcopy, signer):
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer import requires llvm-objcopy and binary-sign-tool "
                "to sign the extension module (dlopen enforces ELF code signature)."
            )
        # OHOS dlopen 强制要求 ELF code signature；HMDFS/SELinux 会忽略 POSIX chmod
        # （E046：chmod 0755 被映射为 0770），因此权限仅作 best-effort 请求，不因
        # HMDFS 返回 0770 判定失败；签名有效性以 .codesign 段 + display-sign 为准。
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1'
            )
            # 签名是最后一个 ELF 内容变更步骤；随后只调整权限（best-effort）并原子替换
            os.chmod(temporary, 0o755)
            os.replace(temporary, path)
            os.chmod(path, 0o755)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")
