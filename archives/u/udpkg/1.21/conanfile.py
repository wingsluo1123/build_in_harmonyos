import os
import shutil

from conan import ConanFile
from conan.tools.files import (get, replace_in_file,
                               apply_conandata_patches,
                               export_conandata_patches)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UdpkgConan(ConanFile):
    name = "udpkg"
    version = "1.21"
    package_type = "application"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/installer-team/udpkg"
    description = ("udpkg — Micro dpkg frontend (Debian installer tool, "
                   "C, tiny ramdisk Debian package handler)")
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # makefile.in: LIBS = -ldebian-installer。udpkg only uses these
        # libdi symbols: di_malloc/di_realloc/di_free, di_exec_shell_log,
        # di_exec_mangle_status, di_debug — all provided by libdi 0.121
        # (static lib + headers). Same requires as cdebootstrap/0.7.9.
        self.requires("libdebian-installer/0.121")

    def build_requirements(self):
        # 无预生成 configure/config.h.in（native 包）——autoreconf 生成；
        # aclocal/automake 用 ohpcd automake/1.18 包（系统 usr/local/bin
        # 属主 20001006 权限 770，CI worker uid 100 无读/执行权限，
        # 'Can't exec "aclocal"' 实测）。本包 configure.ac 无
        # AC_PROG_LIBTOOL（纯 C，无 .lo）——不需要 libtool tool_requirement
        # （同 cdebootstrap）。
        self.tool_requires("automake/1.18")

    # 刻意不设 layout()：makefile.in 用 `$(wildcard *.c)` 收集源文件——
    # basic_layout（out-of-source）会让 OBJS 为空、链接缺目标。保持
    # default layout，Autotools 在 source_folder 内 in-source 构建。

    def source(self):
        # tar 单一顶层目录 udpkg-1.21/（实测）——strip_root 去掉
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.host = "aarch64-unknown-linux-ohos"
        # --build 必须显式传：conan automake 的 config.guess（新版）无法识
        # 别 HarmonyOS（cannot guess build type 实测——同 libdi/cdebootstrap）
        tc.configure_args.extend(["--build=aarch64-unknown-linux-ohos"])
        tc.generate()
        # 依赖 -I/-L 注入（libdi include + lib 路径）——缺它
        # 'debian-installer.h' file not found 实测（同 cdebootstrap）
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        # configure.ac 的 AC_INIT 用 m4_esyscmd(dpkg-parsechangelog) 取版本
        # （环境无 dpkg——'AC_INIT should be called' 实测——同 libdi/
        # cdebootstrap）——硬编码 1.21
        replace_in_file(
            self, os.path.join(self.source_folder, "configure.ac"),
            "m4_esyscmd(dpkg-parsechangelog | perl -ne "
            "'print $1 if m/^Version: (.*)$/;')", "1.21")
        # makefile.in 用 `$(shell dpkg-architecture ...)` 取架构/OS——OHOS
        # 无 dpkg-architecture，命令找不到返回空串，-DARCH_TEXT='' 编译错
        # ——硬编码 arm64/linux（OHOS aarch64 对应 dpkg 架构 arm64）
        mk = os.path.join(self.source_folder, "makefile.in")
        src = open(mk).read()
        src = src.replace("DEB_HOST_ARCH ?= $(shell dpkg-architecture -qDEB_HOST_ARCH)",
                          "DEB_HOST_ARCH ?= arm64")
        src = src.replace("DEB_HOST_ARCH_OS ?= $(shell dpkg-architecture -qDEB_HOST_ARCH_OS)",
                          "DEB_HOST_ARCH_OS ?= linux")
        open(mk, "w").write(src)
        # status.c 用了 open()/O_WRONLY/O_CREAT（lock_fd 状态文件锁）却未
        # #include <fcntl.h>（其 include 链：status.c 自身只列 errno/stdio/
        # string/stdlib/search/sys.file；udpkg.h 也只包含 stdio/config.h/
        # assert.h——configure 探测了 HAVE_FCNTL_H=1 但 status.c 从未引用
        # config.h 的条件宏，clang 隐式函数声明 + 未声明 O_WRONLY 报错实测
        # （status.c:223 'use of undeclared identifier')——补上 <fcntl.h>
        st = os.path.join(self.source_folder, "status.c")
        s0 = open(st).read()
        if "#include <fcntl.h>" not in s0:
            s0 = s0.replace('#include "udpkg.h"\n',
                            '#include "udpkg.h"\n\n#include <fcntl.h>\n')
            open(st, "w").write(s0)
        # 无现成 configure——autoreconf -i 生成；autoconf 用 AUTOCONF 环境
        # 变量指向有效路径（系统 /usr/local/bin/autoconf exit 127 命令找
        # 不到实测）；PERL5LIB 指向 automake-1.18 包内 share（Automake/
        # Config.pm）
        am_pkg = self.dependencies.build["automake"].package_folder
        self.run(
            "AUTOCONF=/data/service/hnp/autoconf.org/autoconf_2.72/"
            "bin/autoconf PATH=%s/bin:/data/service/hnp/"
            "autoconf.org/autoconf_2.72/bin:$PATH PERL5LIB=%s/share/"
            "automake-1.18 autoreconf -i" % (am_pkg, am_pkg),
            cwd=self.source_folder)
        # 修补 autoreconf 生成的 config.sub：automake-1.18 的 config.sub
        # 不认识 OS 'ohos'（--build=aarch64-unknown-linux-ohos 报
        # 'OS 'ohos' not recognized' 实测）——在大名单（portable first）
        # 与 kernel-os 校验两处各加 ohos 分支（同仓库 advancecomp/
        # aalib 的 config.sub 补丁手法，实测两处修补后
        # aarch64-unknown-linux-ohos 通过、linux-gnu 回归正常）
        sub = os.path.join(self.source_folder, "config.sub")
        if os.path.isfile(sub):
            s = open(sub).read()
            if "linux-ohos" not in s:
                s = s.replace(
                    "\tgnu* | android* | bsd* | mach* | minix* | genix* "
                    "| ultrix* | irix* \\",
                    "\tohos* | gnu* | android* | bsd* | mach* | minix* "
                    "| genix* | ultrix* | irix* \\")
                s = s.replace(
                    "\tlinux-gnu*- | linux-dietlibc*- | linux-android*- "
                    "| linux-newlib*- \\",
                    "\tlinux-gnu*- | linux-dietlibc*- | linux-android*- "
                    "| linux-ohos*- | linux-newlib*- \\")
                open(sub, "w").write(s)
        # config.status 的 mktemp 相对路径 ./confXXXXXX（subs1.awk 写入
        # Permission denied 实测——同 libdi/cdebootstrap）——configure 执
        # 行前替换 mktemp 模板（configure 尾部自动执行 config.status——事
        # 后改 config.status 的 ac_tmp 已来不及）
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg):
            src2 = open(cfg).read()
            if "TMPDIR/confXXXXXX" not in src2:
                src2 = src2.replace(
                    'mktemp -d "./confXXXXXX"',
                    'mktemp -d "${TMPDIR}/confXXXXXX"')
                open(cfg, "w").write(src2)
        # 手动 ./configure（in-source）——不走 Autotools helper 的
        # out-of-source 布局（basic_layout 未设，Autotools.configure 默认
        # 在 source_folder 跑；这里直接显式跑，行为与生成的 Makefile 一致）
        # TMPDIR 指可写目录（沙箱 /tmp 只读 + config.status mktemp 需可写）
        # --host 必须单独声明（≠ --build）：仅给 --build 时 autoconf 使
        # host 默认成 build（相同三元组）→ cross_compiling=no → configure
        # 试图运行新编译的 conftest，OHOS clang 产物不可执行，
        # 'cannot run C compiled programs' 硬错误实测（air-quality-sensor）
        #
        # 补 --host=aarch64-unknown-linux-gnu（区别于 build 的 -ohos）→
        # host≠build，cross_compiling 翻转为 yes，跳过运行期 conftest 探测
        self.run("TMPDIR=/data/storage/el2/base/cache "
                 "./configure --build=aarch64-unknown-linux-ohos "
                 "--host=aarch64-unknown-linux-gnu",
                 cwd=self.source_folder)
        # 链接：makefile 手写规则 `$(CC) -o $@ $(OBJS) $(LIBS)` 只用
        # LIBS=-ldebian-installer，不引用 $(LDFLAGS)——AutotoolsDeps 注入
        # 的 -L<libdi>/lib 不生效，ld.lld 报 unable to find library
        # -ldebian-installer 实测——make 命令行覆盖 LIBS 显式带 -L
        ldi = self.dependencies["libdebian-installer"].package_folder
        self.run("make -j4 LIBS=\"-L%s/lib -ldebian-installer\"" % ldi,
                 cwd=self.source_folder)

    def package(self):
        # 静态二进制 → bin/。in-source 构建，产物在 source_folder/udpkg
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "udpkg"), bin_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]