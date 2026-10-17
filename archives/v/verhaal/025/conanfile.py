#!/usr/bin/env python3
"""Conan recipe — verhaal 025

verhaal builds a SQLite database of the Linux kernel stable-branch commits
(including the "Fixes:" trailer graph) so a commit id can be queried to find
out where it was backported to.  Upstream: https://git.sr.ht/~gregkh/verhaal
(tag v025, Greg Kroah-Hartman — used by the kernel CVE team tooling).

Adapted to HarmonyOS PC (aarch64).

Build system: Meson (upstream ships meson.build + autogen.sh).
Dependencies: libgit2, sqlite3, libpcre2-8 (>= 10.42), pthreads.

OHOS 适配要点:
  1. HMDFS 把 /storage 下所有文件的属主归一为共享账号 uid，而进程 euid 是
     另一个 uid，使 libgit2 >= 1.7 的仓库属主校验（GIT_OPT_SET_OWNER_VALIDATION，
     等价 git safe.directory 的库 API 层）对**任何**仓库恒不通过 —— verhaal
     启动即 "Error opening git repo ... is not owned by current user" 退出。
     补丁 0001 在打开失败时关闭该校验重试一次（详见 notes.md；知识库同源条目
     DRAFT-libgit2-1.9.0-owner-validation-hmdfs）。
  2. meson 通过 pkg-config 取 `libpcre2-8`，而 Conan 的 pcre2 包经 PkgConfigDeps
     只产出合并后的 pcre2.pc；包内自带的 libpcre2-8.pc 前缀写死为 '/'，install
     到 Conan 缓存后不可重定位（会展开成 -I//include）。故 generate() 按实际
     安装路径补一个 libpcre2-8.pc 别名。
  3. 产物是命令行工具（bin/verhaal），非库 —— 软件级声明 commands.json（R38）。
  4. meson 以「命令名」探测 ar/ranlib/pkg-config（内部走 subprocess 的 PATH 查找）。
     OHOS 上该查找不可靠：本机实测 `llvm-ar --version` 直接可执行，但 meson 经
     subprocess 调用时报 `Errno 2: No such file or directory`，导致
     `meson.build:4:0: ERROR: Unknown linker(s): [['llvm-ar']]`。故 generate()
     将三者以绝对路径写入 MesonToolchain 生成的 machine 文件（与仓库既有
     meson 配方同款对策）。
"""
import os
import re
import shutil
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

# CI worker 的沙箱对进程/句柄配额有硬限：并行 spawn 会被 `/bin/sh: can't fork -
# try again` / `ninja: fatal: posix_spawn: Resource temporarily unavailable` 打断
# （CI #93650/#93687/#93996，见 notes.md 问题 7）。conan 的 Meson.build() 并行度
# 取 CPU 数（实测 20）最糟，`-j2` 在 worker 满载时仍会失败，故本包直接顺序编译
# （仅 7 个源文件 + 1 个可执行目标，代价可忽略）。
_MESON_JOBS = 1
# 仅命中「进程创建失败」特征才退避重试；重试路径不 fork（time.sleep + 进程内读日志）。
# 实测 worker 饱和可持续 100s 以上（CI #93996 连续 5 次命中），故给足骑过窗口的耐心。
_FORK_RETRY_ATTEMPTS = 10
_FORK_RETRY_WAIT = 30  # 秒
# 转录为空（shell 根本没起来）与「静默失败」无法区分，故只给有限次重试
_EMPTY_OUTPUT_RETRIES = 2
# 判定要求 EAGAIN 与 fork/spawn 语境同行，避免把磁盘/内存/文件锁类 EAGAIN 误判为基建
_FORK_FAILURE_PATTERNS = (
    re.compile(r"(?:posix_spawn|fork|spawn)[^\n]{0,80}Resource temporarily unavailable"),
    re.compile(r"Resource temporarily unavailable[^\n]{0,80}(?:posix_spawn|fork)"),
    re.compile(r"(?:can'?t|cannot) fork"),
    re.compile(r"fork: retry"),
    re.compile(r"No record of process"),
)


class VerhaalConan(ConanFile):
    name = "verhaal"
    version = "025"
    description = "Linux stable-branch commit parse and query tool (verhaal)"
    license = "GPL-2.0-only"
    homepage = "https://git.sr.ht/~gregkh/verhaal"
    url = "https://git.sr.ht/~gregkh/verhaal"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    # R32: OHOS 与 Linux 同族
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # meson.build 硬性要求：sqlite3 >= 3.40 / libgit2 >= 1.5 / libpcre2-8 >= 10.42
        self.requires("libgit2/1.9.0")
        self.requires("sqlite3/3.53.4")
        self.requires("pcre2/10.45")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._alias_pcre2_pc()
        toolchain = MesonToolchain(self)
        # 上游 autogen.sh 用 meson setup，无子项目/wrap 依赖
        toolchain.project_options["wrap_mode"] = "nodownload"
        # 消除产物内本包的源码/构建机绝对路径（鸿蒙专项测试 T2）
        toolchain.extra_cflags = [
            f"-ffile-prefix-map={self.source_folder}=.",
            f"-ffile-prefix-map={self.build_folder}=.",
        ]
        toolchain.generate()
        self._inject_meson_tools()

    def build(self):
        # 复刻 conan Meson.configure()/build() 的命令行，唯一目的是**把输出落盘**：
        # conan 的 run() 不透传输出给配方，失败时只剩 "Error N while executing"，
        # 无法判定是否属进程创建失败。CI 上两步都被 fork 枯竭打死过：
        #   * build #93650：`conanbuildenv-*.sh[13]: can't fork - try again`（setup 步）
        #   * build #93687：`ninja: fatal: posix_spawn: ...`（compile 步）
        self._meson_step("setup", self._meson_setup_command(), "meson-setup.log")
        self._meson_step("compile", self._meson_compile_command(), "meson-compile.log")

    # ── helpers ────────────────────────────────────────────────────────────

    def _meson_setup_command(self):
        """复刻 conan ``Meson.configure()`` 的命令行（machine 文件与 prefix 语义一致）。"""
        generators = self.generators_folder
        native = os.path.join(generators, MesonToolchain.native_filename)
        cross = os.path.join(generators, MesonToolchain.cross_filename)
        machine_files = list(self.conf.get(
            "tools.meson.mesontoolchain:extra_machine_files",
            default=[], check_type=list) or [])
        is_cross_build = os.path.exists(cross)

        command = "{} setup ".format(self._meson_executable())
        if is_cross_build:
            machine_files.insert(0, cross)
            command += " ".join('--cross-file "{}"'.format(item) for item in machine_files)
        if os.path.exists(native):
            if not is_cross_build:
                machine_files.insert(0, native)
                command += " ".join('--native-file "{}"'.format(item) for item in machine_files)
            else:
                command += ' --native-file "{}"'.format(native)
        command += ' "{}" "{}"'.format(self.build_folder, self.source_folder)
        # conan 的 Meson._prefix：把安装前缀固定为 Unix 根（Windows 上亦用正斜杠）
        command += " --prefix={}".format(os.path.abspath("/").replace("\\", "/"))
        return command

    def _meson_compile_command(self):
        """复刻 conan ``Meson.build()`` 的命令行，但并行度固定为 ``_MESON_JOBS``。"""
        command = '{} compile -C "{}" -j{}'.format(
            self._meson_executable(), self.build_folder, _MESON_JOBS)
        verbosity = self._meson_verbosity()
        if verbosity:
            command += " " + verbosity
        return command

    def _meson_install_command(self):
        """复刻 conan ``Meson.install()`` 的命令行（--destdir / verbosity / strip）。"""
        command = '{} install -C "{}" --destdir "{}"'.format(
            self._meson_executable(), self.build_folder.replace("\\", "/"),
            self.package_folder.replace("\\", "/"))
        verbosity = self.conf.get("tools.build:verbosity", choices=("quiet", "verbose"))
        if verbosity == "quiet":
            command += " --quiet"
        try:
            do_strip = self.conf.get("tools.build:install_strip", check_type=bool)
        except ConanException:
            do_strip = "meson" in (self.conf.get("tools.build:install_strip",
                                                 check_type=list) or [])
        if do_strip:
            command += " --strip"
        return command

    def _meson_step(self, label, command, log_name):
        """执行一条 meson 命令：输出落盘 + 仅对进程创建失败（fork EAGAIN）退避重试。

        CI worker 的沙箱对进程/句柄配额有硬限：conan 的 ``Meson.build()`` 并行度取
        ``tools.build:jobs``（worker 未设该 conf → 回落 CPU 数，实测 20），ninja
        并发 spawn（ninja → sh → clang → ld）会打满配额：

            ninja: fatal: posix_spawn: Resource temporarily unavailable

        重试路径**完全不 fork**：backoff 用 ``time.sleep``，读日志与特征匹配都在
        进程内完成。shell 版重试自身依赖 sleep/cat/grep 等外部命令，配额枯竭时
        重试机制先死（pgqd 教训，PR #16073）。只有命中「fork/spawn + EAGAIN」语境
        或转录为空才重试；其他任何失败首次即失败并打印完整转录，避免把真错误
        掩盖成基础设施抖动。
        """
        log_path = os.path.join(self.build_folder, log_name)
        silent_attempts = 0
        for attempt in range(1, _FORK_RETRY_ATTEMPTS + 1):
            try:
                # 输出落盘而非直接透传：失败后按特征判定（读文件不 fork），
                # 无论成败都在下方回放到 CI 日志
                retcode = self.run('{} > "{}" 2>&1'.format(command, log_path),
                                   ignore_errors=True)
            except ConanException:
                # 连 shell 都起不来（fork 枯竭的另一种表现），日志可能尚未写出
                retcode = -1
            output = self._read_build_log(log_path)
            if retcode == 0:
                self.output.info(output)
                return
            self.output.error(output)

            signature = self._fork_failure(output)
            if not output.strip():
                silent_attempts += 1
                retryable = silent_attempts <= _EMPTY_OUTPUT_RETRIES
                reason = "转录为空（进程未能启动）"
            else:
                retryable = signature is not None
                reason = "进程创建失败特征命中: {}".format(signature)
            if attempt == _FORK_RETRY_ATTEMPTS or not retryable:
                raise ConanException("meson {} failed (exit {})".format(label, retcode))
            self.output.warning(
                "meson {}: {}（第 {}/{} 次重试），{}s 后重试".format(
                    label, reason, attempt, _FORK_RETRY_ATTEMPTS - 1, _FORK_RETRY_WAIT)
            )
            time.sleep(_FORK_RETRY_WAIT)

    @staticmethod
    def _meson_executable():
        return shutil.which("meson") or "meson"

    def _meson_verbosity(self):
        """对齐 conan ``Meson._build_verbosity``（tools.compilation:verbosity）。"""
        verbosity = self.conf.get("tools.compilation:verbosity",
                                  choices=("quiet", "verbose"))
        return "--verbose" if verbosity == "verbose" else ""

    @staticmethod
    def _read_build_log(path):
        try:
            with open(path, encoding="utf-8", errors="ignore") as handle:
                return handle.read()
        except OSError:
            return ""

    @staticmethod
    def _fork_failure(output):
        """返回命中的进程创建失败特征（无命中返回 None）。"""
        for pattern in _FORK_FAILURE_PATTERNS:
            match = pattern.search(output)
            if match:
                return match.group(0).strip()[:120]
        return None

    def package(self):
        # 上游仓以 SPDX 声明许可（无单一 LICENSE 文件）。install 步同样走退避重试：
        # meson install 内部也要 spawn（ninja/cp），worker 饱和时一样会被打断。
        self._meson_step("install", self._meson_install_command(), "meson-install.log")

    def package_info(self):
        # 命令行工具，非库
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

    # ── helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _first_existing(directories, names):
        """在给定目录列表中查找首个存在的可执行文件，返回绝对路径。"""
        for directory in directories:
            if not directory or not os.path.isdir(directory):
                continue
            for name in names:
                candidate = os.path.join(directory, name)
                if os.path.isfile(candidate):
                    return candidate
        return None

    def _inject_meson_tools(self):
        """把 ar/ranlib/pkg-config 的绝对路径写进 MesonToolchain 的 machine 文件。

        meson 探测这些工具时按「命令名」调用（subprocess 的 PATH 查找），OHOS 上
        该查找不可靠 —— 经 subprocess 调用报 Errno 2，导致
        `ERROR: Unknown linker(s): [['llvm-ar']]`。写绝对路径即绕过探测。
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}

        directories = []
        for key in ("c", "cpp"):
            compiler = compilers.get(key) or ""
            if os.path.sep in compiler:
                directories.append(os.path.dirname(compiler))
        # conan 的 buildenv 会把工具链 bin 挂到 PATH 上（含 llvm-ar 符号链接）
        directories.extend(entry for entry in os.environ.get("PATH", "").split(os.pathsep) if entry)

        ar = compilers.get("ar") or self._first_existing(directories, ("llvm-ar", "ar"))
        ranlib = compilers.get("ranlib") or self._first_existing(
            directories, ("llvm-ranlib", "ranlib")
        )
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = self._first_existing(directories, ("pkg-config", "pkgconf"))

        insert = [f"{key} = '{value}'" for key, value in
                  (("ar", ar), ("ranlib", ranlib), ("pkg-config", pkg_config)) if value]
        if not insert:
            self.output.warning("meson 工具注入: 未找到 ar/ranlib/pkg-config，跳过")
            return

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            missing = [line for line in insert
                       if f"\n{line.split(' =')[0]} =" not in content]
            if missing:
                content = content.replace(
                    "[binaries]\n", "[binaries]\n" + "\n".join(missing) + "\n", 1
                )
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)
        self.output.info(f"meson 工具注入: ar={ar} ranlib={ranlib} pkg-config={pkg_config}")

    def _alias_pcre2_pc(self):
        """meson 依赖 `libpcre2-8`，而 PkgConfigDeps 只为 pcre2 包产出 pcre2.pc。

        pcre2 包内自带的 libpcre2-8.pc 前缀写死为 '/'（构建时的安装前缀），
        Conan 缓存内不可重定位，直接使用会得到 -I//include。这里依据依赖包
        的真实路径生成等价别名，供 meson 的 dependency('libpcre2-8') 解析。
        """
        dependency = self.dependencies["pcre2"]
        package_folder = dependency.package_folder

        def first_absolute(paths, default):
            for path in paths:
                return path if os.path.isabs(path) else os.path.join(package_folder, path)
            return os.path.join(package_folder, default)

        includedir = first_absolute(dependency.cpp_info.includedirs, "include")
        libdir = first_absolute(dependency.cpp_info.libdirs, "lib")
        content = [
            f"prefix={package_folder}",
            "exec_prefix=${prefix}",
            f"libdir={libdir}",
            f"includedir={includedir}",
            "",
            "Name: libpcre2-8",
            "Description: PCRE2 8-bit library (alias emitted for the Conan pcre2 package)",
            f"Version: {dependency.ref.version}",
            "Libs: -L${libdir} -lpcre2-8",
            "Cflags: -I${includedir}",
            "",
        ]
        save(self, os.path.join(self.generators_folder, "libpcre2-8.pc"), "\n".join(content))
        self.output.info(f"libpcre2-8.pc alias -> include={includedir} lib={libdir}")
