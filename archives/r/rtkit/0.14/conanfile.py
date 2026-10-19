#!/usr/bin/env python3
"""Conan recipe — rtkit 0.14（RealtimeKit：D-Bus 实时调度策略服务）

rtkit 是 D-Bus 系统服务，按客户端请求把用户进程/线程的调度策略改为
SCHED_RR（实时）或提升 nice 级别，是 PipeWire/JACK 等低延迟音频栈的
授权中间层。上游产物三个可执行程序：

  * rtkit-daemon —— 服务本体（默认 /usr/libexec）
  * rtkitctl     —— 控制工具（sbin）
  * rtkit-test   —— 自测客户端（installed-tests）

Meson 构建，硬依赖 dbus-1 与 libcap；libsystemd 在 OHOS 上关闭，
polkit-gobject-1 为可选依赖（运行时经 D-Bus 向 polkit 服务鉴权）。
"""
import contextlib
import os
import re
import shutil
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class RtkitConan(ConanFile):
    name = "rtkit"
    version = "0.14"
    description = "RealtimeKit — D-Bus 服务，按请求把用户进程/线程提升为 SCHED_RR 实时调度"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.freedesktop.org/pipewire/rtkit"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: 平台判断必须同时接受 Linux 与 OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("rtkit 仅支持 Linux/OHOS")

    def requirements(self):
        self.requires("dbus/1.14.10")
        self.requires("libcap/2.69")

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        # ninja 由 profile 的 buildenv PATH（/data/service/hnp/bin）提供
        # 0.14 的 gitlab 归档不含预生成的 xml-introspection.h，meson 需要
        # xxd 把 D-Bus 自省 XML 转成 C 数组；系统 xxd 在 CI 镜像上不保证存在。
        self.tool_requires("xxd/9.1.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options.update({
            # OHOS 无 systemd，sd_notify 走 systemd/sd-daemon.h，必须关闭
            "libsystemd": "disabled",
            # 安装路径全部锚定到包前缀：dbus-1.pc 里携带的是构建机绝对路径
            # （system_bus_services_dir 等），不覆盖会装到包外并被 conan 丢弃
            "bindir": "bin",
            "sbindir": "bin",
            "libexecdir": "libexec",
            "dbus_systemservicedir": "share/dbus-1/system-services",
            "dbus_interfacedir": "share/dbus-1/interfaces",
            "dbus_rulesdir": "share/dbus-1/system.d",
            "polkit_actiondir": "share/polkit-1/actions",
            "systemd_systemunitdir": "lib/systemd/system",
        })
        tc.generate()
        PkgConfigDeps(self).generate()
        self._alias_dbus_pc()
        self._pin_meson_archiver()

    def _pin_meson_archiver(self):
        """把归档器（静态链接器）的绝对路径写进 meson native file。

        Conan 的 MesonToolchain 只在 Android NDK 分支给 native file 写 `ar`，
        其余情况留空，meson 便自行猜测：clang 下猜出裸名 `llvm-ar` 并按 PATH
        查找。CI worker 的执行 PATH 只有 /data/app/bin:/system/bin:...，不含
        /data/service/hnp/bin，于是 meson setup 在第一步就失败（实测 CI #93569）：

            ../meson.build:1:0: ERROR: Unknown linker(s): [['llvm-ar']]
            Running `llvm-ar --version` gave "[Errno 2] No such file or directory"

        这里用 profile 已提供的编译器目录推出归档器绝对路径（优先 llvm-ar，
        回退 ar）写进 [binaries]，使构建不再依赖 PATH（与 account-utils 手动
        传 `AR=` 同效，但走 native file 更稳）。
        """
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c")
        if not cc:
            self.output.warning("未配置 tools.build:compiler_executables，跳过归档器锚定")
            return
        tool_dir = os.path.dirname(cc)
        archiver = next((os.path.join(tool_dir, name) for name in ("llvm-ar", "ar")
                         if os.path.isfile(os.path.join(tool_dir, name))), None)
        if archiver is None:
            self.output.warning(f"{tool_dir} 下既无 llvm-ar 也无 ar，跳过归档器锚定")
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if re.search(r"^\s*ar\s*=", content, re.MULTILINE):
            return
        content = content.replace("[binaries]",
                                  f"[binaries]\nar = '{archiver}'", 1)
        with open(native_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _alias_dbus_pc(self):
        """把 PkgConfigDeps 产出的 dbus.pc 复制为上游要求的 dbus-1.pc。

        dbus/1.14.10 配方未声明 pkg_config_name，PkgConfigDeps 于是生成
        dbus.pc，而 rtkit 的 meson.build 查找 dependency('dbus-1')。
        安装目录变量（interfaces_dir/system_bus_services_dir）已在
        project_options 中显式指定，故别名只需保证依赖可被发现。
        """
        src = os.path.join(self.generators_folder, "dbus.pc")
        dst = os.path.join(self.generators_folder, "dbus-1.pc")
        if not os.path.isfile(src):
            self.output.warning("未生成 dbus.pc，跳过 dbus-1.pc 别名")
            return
        with open(src, encoding="utf-8") as handle:
            content = handle.read()
        with open(dst, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        self._run_with_spawn_retry(meson.configure, "meson setup",
                                   on_retry=self._reset_meson_build_state)
        self._run_with_spawn_retry(meson.build, "meson compile")

    # CI worker 上偶发的 fork/posix_spawn 资源耗尽（EAGAIN），属基建抖动（同包换
    # worker 常可过），故只对这一签名做有限次退避重试；非该签名的失败（真实编译/
    # 链接错误）首次即抛出，不做盲目重试（R43）。已实测两种形态：
    #
    #   * CI #93599 —— meson setup 第一次 clang 调用起不来：
    #       ERROR: Unable to detect linker for compiler `<clang> -Wl,--version`
    #       stderr: clang-15: error: unable to execute command: posix_spawn failed:
    #               Resource temporarily unavailable
    #   * CI #93688 —— 连 conan 生成的 env 脚本都 fork 不动（该脚本用
    #     `$(printenv …)` 拼反注册脚本，需要 fork）：
    #       /system/bin/sh: …/conanbuildenv-release-armv8.sh[13]: can't fork - try again
    #
    # 判定必须看**命令输出**而非异常消息：``ConanFile.run()`` 在命令非零退出时只抛
    # ``ConanException("Error 1 while executing")``，子进程的 stderr 不进异常 ——
    # 只看 ``str(exc)`` 的重试永远不可能命中，上一版即因此形同虚设（CI #93688
    # 实测直接打红）。故把这一步的命令输出落到日志，再按日志内容判定（与
    # megactl / zrc 的 ``_run_logged`` 同源做法）。
    _SPAWN_FAIL_SIGNATURES = (
        "Resource temporarily unavailable",
        "posix_spawn failed",
        "unable to execute command",
        "can't fork",
        "cannot fork",
        "fork: retry",
        "Cannot allocate memory",
    )
    _SPAWN_RETRY_DELAYS = (30, 60, 120, 180)

    def _run_with_spawn_retry(self, step, label, on_retry=None):
        """执行一步 meson 调用，命中 spawn 耗尽签名时退避重试。

        :param step: 无参可调用对象（``Meson.configure`` / ``Meson.build``）
        :param label: 日志与提示里用的可读名称
        :param on_retry: 重试前置动作（setup 需先清掉上次失败留下的 meson 状态）
        """
        log_path = os.path.join(self.source_folder,
                                "conan-%s.log" % label.replace(" ", "-"))
        for attempt, delay in enumerate((0,) + self._SPAWN_RETRY_DELAYS):
            if delay:
                self.output.warning(
                    f"{label} 命中 worker spawn 资源耗尽（第 {attempt} 次），"
                    f"{delay}s 后重试…")
                time.sleep(delay)
                if on_retry is not None:
                    on_retry()
            try:
                with self._log_run_output(log_path):
                    step()
            except ConanException:
                self._echo_log(log_path)
                if not self._log_has_spawn_error(log_path):
                    raise
                if attempt == len(self._SPAWN_RETRY_DELAYS):
                    self.output.error(
                        f"{label} 连续 {attempt + 1} 次因 worker spawn 资源耗尽失败，"
                        "日志中未见真实编译/链接错误；建议换 worker 重触发")
                    raise
            else:
                self._echo_log(log_path)
                return

    @contextlib.contextmanager
    def _log_run_output(self, log_path):
        """把这一步里 conan 自己发起的命令输出改写到日志文件。

        ``Meson.configure()`` / ``Meson.build()`` 内部调用
        ``self._conanfile.run(cmd)`` 且不接受 stdout 参数，故临时替掉实例上的
        ``run``：命令仍由 conan 拼装（machine file、--prefix 都不变），只是把
        stdout/stderr 指向日志。重定向不是管道，退出码仍是命令本身的退出码。
        """
        original_run = self.run

        def logged_run(command, **kwargs):
            kwargs.setdefault("stdout", log)
            kwargs.setdefault("stderr", log)
            return original_run(command, **kwargs)

        with open(log_path, "w", encoding="utf-8", errors="replace") as log:
            self.run = logged_run
            try:
                yield
            finally:
                self.run = original_run

    def _echo_log(self, log_path):
        """回显被重定向走的命令输出。

        否则 CI 日志里既看不到编译输出也看不到告警，评审无从定位。
        """
        if not os.path.isfile(log_path):
            return
        with open(log_path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                self.output.writeln(line.rstrip())

    def _log_has_spawn_error(self, log_path):
        """日志里是否出现 spawn/fork 资源性失败签名。"""
        if not os.path.isfile(log_path):
            return False
        with open(log_path, encoding="utf-8", errors="replace") as handle:
            body = handle.read()
        return any(sig in body for sig in self._SPAWN_FAIL_SIGNATURES)

    def _reset_meson_build_state(self):
        """清掉上次 setup 中途失败留下的 meson 状态，使重试是全新配置。

        meson 以 ``<build>/meson-private/coredata.dat`` 判定"目录已配置"，存在时
        再跑 setup 会要求 ``--reconfigure``/``--wipe`` 而拒绝配置。conan 生成的
        ``conan/`` 目录（native file、*.pc）必须保留，故只删 meson 自己的产物。
        """
        for name in ("meson-private", "meson-info", "meson-logs", "build.ninja",
                     "compile_commands.json"):
            path = os.path.join(self.build_folder, name)
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.isfile(path):
                os.remove(path)

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "GPL", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        """给包内所有 ELF 打上 OHOS 自签名。

        鸿蒙内核对未签名的可执行文件直接返回 EPERM（"Operation not
        permitted"），本机 `rtkit-daemon --help` 实测如此；签名后可在真机执行。
        """
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"缺少 OHOS 签名工具: {tool}")

        targets = []
        for subdir in ("bin", "libexec"):
            root = os.path.join(self.package_folder, subdir)
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in filenames:
                    path = os.path.join(dirpath, name)
                    if os.path.isfile(path) and not os.path.islink(path) and self._is_elf(path):
                        targets.append(path)

        for target in sorted(targets):
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1')

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # rtkit-daemon 按上游约定装在 libexec/，rtkitctl 在 bin/
        self.cpp_info.bindirs = ["bin", "libexec"]
        for binary_dir in ("bin", "libexec"):
            path = os.path.join(self.package_folder, binary_dir)
            self.runenv_info.append_path("PATH", path)
            self.buildenv_info.append_path("PATH", path)
