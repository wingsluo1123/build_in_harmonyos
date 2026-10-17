#!/usr/bin/env python3
"""Conan recipe — spectools 201601r1（autotools / C，Kismet Wi-Spy 频谱仪工具集）.

spectools 是 Metageek Wi-Spy USB 频谱仪的用户态工具集：spectool_raw
（原始终端频谱读取）、spectool_curses（ncurses 终端界面）、spectool_net
（远程设备网络服务器）。GTK 客户端（spectool_gtk）仅在 pkg-config 探测到
gtk+-2.0 时构建——OHOS 无 GTK，configure 按其自身逻辑自然降级
（AC_MSG_WARN，非错误）。

上游：http://www.kismetwireless.net/spectools/（Kismet 官网；Debian 包
声明的同源地址）。官方归档 spectools-2016-01-R1.tar.xz 位于
kismetwireless.net/code/ 目录（2026-10-14 实测 HTTP 200，120732 字节）；
文件名经 Debian uversionmangle 映射为版本号 201601r1
（s/(\d\d\d\d)-(\d\d)-R(.*)/$1$2r$3/）。

构建系统：autotools（tarball 预生成 configure 2.69，无需 autoreconf
自举）。自带 config.sub 为 2001-06-08 版，不认识 aarch64 CPU 与
linux-ohos OS（E122）→ 补丁替换为 autoconf 2.71 config.sub 并添加
linux-ohos 识别（judy/1.0.5 整文件替换先例）。

硬依赖（configure.in）：
  - libusb 0.1.x API（AC_CHECK_HEADER usb.h + AC_CHECK_LIB usb_init）：
    configure 明确拒绝 libusb 1.x（"Libusb 1.x.x not currently
    supported"），libusb-compat/0.1.7 提供 0.1 兼容层（ohpcd 已发布，
    2026-10-14 conan list 活查 + 本地缓存 armv8 二进制在位）。
  - pthread / libm（sysroot 内置）。
  - ncurses（spectool_curses 目标，configure 探测到即启用）：
    ncurses/6.6（ohpcd 已发布）。

鸿蒙适配要点：
  - E122：2001 版 config.sub 不识别 aarch64-unknown-linux-ohos → 补丁
    0001 替换为 autoconf 2.71 版并补 linux-ohos kernel-os 识别。
  - E011/E129：configure 两处 umask 077 在 HMDFS 产生 setgid 不可写
    临时目录 → 补丁 0003 剥离（mfterm 同款修复）。
  - Makefile.in 的 .depend 规则用 $(CXX) $(CFLAGS) -MM 对全部 .c 文件
    （含 GTK）做增量依赖扫描；交叉环境宿主 CXX 看不到 conan 依赖头、
    GTK 对象未配置 → 补丁 0002 禁用依赖扫描（conan 一次性构建无增量
    需求）。
  - configure 无 AC_RUN_IFELSE（仅 AC_LINK_IFELSE），OHOS 下显式传
    --build/--host 三元组（mfterm 同款），交叉环境安全。
  - E074：HMDFS 上 make -j1（同 mfterm）。
  - 树内构建：Makefile.in 用旧式 .c.o 后缀规则，GNU make 后缀规则不做
    VPATH 搜索 → out-of-tree 构建直接 "No rule to make target"，在源码
    目录就地 configure + make。
  - ncurses：ohpcd ncurses/6.6 只发布宽字符静态库（package_info.libs =
    ["ncursesw","panelw","menuw","formw"]，无 libncurses.a）→ 补丁 0004
    将 configure 的 curses 库检查/链接改为 -lncursesw（API 同源，C 代码
    未用宽字符接口）。

上游未提供正式自动测试（源码树无 test 目录、Makefile.in 无 TESTS 目标、
无测试框架引用），以 test_package 消费者冒烟 + 鸿蒙特有测试验证。

License: GPL-2.0-or-later
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SpectoolsConan(ConanFile):
    name = "spectools"
    version = "201601r1"
    description = "Utilities for using the Wi-Spy USB spectrum analyzer hardware (Kismet spectools)"
    license = "GPL-2.0-or-later"
    homepage = "http://www.kismetwireless.net/spectools/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: 判断必须同时考虑 Linux 与 OHOS 两种取值
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("spectools is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # 两个依赖均已发布制品仓（W0/R36：2026-10-14 conan list 活查
        # ohpcd + 本地缓存 armv8 二进制在位）
        # configure 要求 libusb 0.1.x API（usb.h + usb_init）；
        # libusb-compat 提供 0.1 兼容层，libusb/1.0.x 被 configure 明确
        # 拒绝
        self.requires("libusb-compat/0.1.7")
        # spectool_curses 目标（configure 探测到 ncurses 即自动启用）
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # m4/1.4.19 范式：profile 的 tools.build:compiler_executables
            # 与 [buildenv] CONFIG_SHELL 在部分 worker 上不存在（本机
            # /data/service/hnp/bin/{clang,bash} 均缺失），经 toolchain
            # environment() 用校验过的工具路径覆盖（写进
            # conanautotoolstoolchain.sh，聚合 conanbuild.sh 中排在
            # conanbuildenv-*.sh 之前，优先生效）
            env = tc.environment()
            env.define("CONFIG_SHELL", self._select_shell())
            env.define("SHELL", self._select_shell())
            cc = self._select_tool_command("c", ["clang", "gcc", "cc"])
            if cc:
                env.define("CC", cc)
            cxx = self._select_tool_command("cpp", ["clang++", "g++", "c++"])
            if cxx:
                env.define("CXX", cxx)
            tc.generate(env=env)
        else:
            tc.generate()
        # AutotoolsDeps 注入依赖的 CPPFLAGS/LDFLAGS/LIBS（-I<libusb-compat>
        # /include -L<libdir> -lusb -lncursesw…），configure 的 usb.h/
        # usb_init/initscr 检查与 make 链接都依赖这些 flags
        AutotoolsDeps(self).generate()
        # configure 编译的 conftest 需在运行时加载 conan 包动态库（防御：
        # mfterm 同款，当前依赖均为静态库，无实际加载需求）
        env2 = Environment()
        libdirs = set()
        for dep in self.dependencies.host.values():
            for d in dep.cpp_info.aggregated_components().libdirs:
                libdirs.add(d)
        for libdir in sorted(libdirs):
            env2.prepend_path("LD_LIBRARY_PATH", libdir)
        env2.vars(self).save_script("spectools-build-env")

    def build(self):
        apply_conandata_patches(self)
        self._run_configure()
        # E074: HMDFS 并行 make 触发 jobserver fifo EPERM → -j1
        # 树内构建：Makefile.in 用旧式 .c.o 后缀规则，GNU make 后缀规则
        # 不做 VPATH 搜索 → out-of-tree 直接 "No rule to make target
        # 'spectool_container.o'"。在源码目录（conan 复制到 build folder
        # 根部的拷贝）就地 configure + make。
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # Makefile install 目标：仅安装 $(TARGETS) 二进制到 $(BIN)
        # （spectool_raw/spectool_net/spectool_curses；tarball 无 man 页）
        self.run("make install DESTDIR=%s" % shlex.quote(self.package_folder),
                 cwd=self.source_folder, env="conanbuild")

    def package_info(self):
        # 命令行工具，无库导出（mfterm/m1ddc 同款）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)

    def _run_configure(self):
        # R33: CC/CFLAGS/LDFLAGS/LIBS 全部由聚合 conanbuild 环境注入
        # （conanautotoolstoolchain.sh + conanbuildenv-*.sh）。
        # --prefix=/ 与 DESTDIR=package_folder 组合（conan Autotools
        # 标准语义）→ 产物直接落 package_folder/bin/。
        configure = os.path.join(self.source_folder, "configure")
        args = ["--prefix=/"]
        if self.settings.os == "OHOS":
            # AC_CANONICAL_HOST + 2001 版 config.guess 无法探测 HarmonyOS；
            # 显式传 --build/--host 三元组（补丁 0001 后 config.sub 支持
            # *-linux-ohos，同 mfterm 做法）。configure 仅含
            # AC_LINK_IFELSE，无运行时探测，交叉环境安全。
            triplet = "aarch64-unknown-linux-ohos"
            args += ["--build=%s" % triplet, "--host=%s" % triplet]
            # profile [buildenv] 的 CONFIG_SHELL 在部分 worker 不存在
            # （configure re-exec 会 127）；用校验过的 shell 命令行前缀
            # 覆盖（前缀 env 优先级高于脚本 export）
            shell = self._select_shell()
            self.run(
                "CONFIG_SHELL=%s SHELL=%s %s %s" % (
                    shlex.quote(shell), shlex.quote(shell),
                    shlex.quote(configure),
                    " ".join(shlex.quote(a) for a in args)),
                cwd=self.source_folder,
                env="conanbuild",
            )
        else:
            self.run("%s %s" % (shlex.quote(configure),
                                " ".join(shlex.quote(a) for a in args)),
                     cwd=self.source_folder,
                     env="conanbuild")

    def _select_tool_command(self, conf_key, candidates):
        """首选 profile tools.build:compiler_executables（指向 OHOS 交叉
        编译器，如 /opt/lpk-fixed/clang，-dumpmachine=
        aarch64-unknown-linux-ohos）；回退 PATH 上的编译器名（无 profile
        conf 的 CI worker 上即 worker 的 OHOS 编译器）。WSL 上 PATH 裸名
        是构建机原生编译器（/usr/bin/clang → x86_64），conf 在位时必须
        以 conf 为准，否则 configure 直接 "C compiler cannot create
        executables"。"""
        try:
            exe = self.conf.get("tools.build:compiler_executables",
                                check_type=dict, default={})
        except Exception:
            exe = {}
        cand = exe.get(conf_key)
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
        for candidate in candidates:
            command = shutil.which(candidate)
            if command:
                return command
        return None

    @staticmethod
    def _select_shell():
        """configure/生成的 Makefile 会缓存 CONFIG_SHELL。ohos-aarch64
        profile 写死的 /data/service/hnp/bin/bash 在部分 worker 上不存在
        （本机实测 ls 报 No such file），候选回退（mfterm 同款）。"""
        for shell in (os.environ.get("CONFIG_SHELL"),
                      os.environ.get("SHELL"),
                      "/data/service/hnp/bin/bash",
                      "/bin/sh",
                      "/system/bin/sh"):
            if not shell:
                continue
            if os.path.isabs(shell):
                if os.path.isfile(shell) and os.access(shell, os.X_OK):
                    return shell
            elif shutil.which(shell):
                return shell
        return "sh"
