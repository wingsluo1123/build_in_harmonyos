#!/usr/bin/env python3
"""Conan recipe — toilet 0.3.r155.3eb9d58 (cacalabs/toilet).

toilet — "The Other Implementation of figLET": renders plain text as large
colour ASCII-art from FIGlet .flf/.tlf fonts, with libcaca filters and
HTML/IRC/TGA export.

Build system: Autotools (configure.ac + Makefile.am). The upstream source
archive is a git-archive snapshot and therefore ships **no** generated
``configure``/``Makefile.in``; build() bootstraps them with the upstream
``bootstrap`` script, using automake from build_requirements() (the device
only provides the autoconf family, see E178/E248).
"""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class ToiletConan(ConanFile):
    name = "toilet"
    version = "0.3.r155.3eb9d58"
    description = ("toilet — render plain text as large colour ASCII/ANSI art "
                   "using FIGlet fonts, with libcaca filters and HTML/IRC export")
    license = "WTFPL"
    homepage = "https://github.com/cacalabs/toilet"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        # 源码内构建：上游两个官方测试脚本按**源码树相对路径**取值
        # （test/check-source 读 `../src/*.c`，test/check-fonts 读 `../fonts`），
        # 只在 srcdir == builddir 时成立。conan 默认的 basic_layout 把构建目录放在
        # build-release/ 子目录（即 VPATH 构建），会让这两个上游测试报
        # "No such file or directory"/"could not load font" 而假失败；
        # 改为 build="." 后源码与构建同目录（no_copy_source 默认 False，
        # 源码本身已复制进 build_folder），上游测试即可原样运行、无需改动上游文件。
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def export_sources(self):
        # 补丁必须随配方导出到 source 目录，否则 apply_conandata_patches 在
        # 干净 cache 里找不到 patches/*.patch（实测 FileNotFoundError）。
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac 里 PKG_CHECK_MODULES(CACA, caca >= 0.99.beta18) 是硬检查：
        # 没有 libcaca 时 configure 直接 AC_MSG_ERROR 退出。
        self.requires("libcaca/0.99.beta20.1")

    def build_requirements(self):
        # 源码归档不含 configure/aclocal.m4/Makefile.in（git archive 快照），
        # build() 必须先自举。本机 /data/service/hnp/bin 只有 autoconf 家族
        # （autoconf/autoheader/autoreconf/m4），**没有** automake/aclocal；
        # 制品仓已发布 automake/1.18（aclocal+automake，其 package_info 自带
        # PERL5LIB/ACLOCAL_PATH 注入），故以 tool_requires 拉入。
        # 不声明 libtool：configure.ac 无 AC_PROG_LIBTOOL，上游 bootstrap 也不会找 libtoolize。
        # 不声明 autoconf：SDK 已提供 autoconf 2.72，而 conan 侧 autoconf 会拉入
        # OHOS 版 perl，其 XS 模块与 SDK perl 5.42.0 冲突（同 accel-config/4.1.9 先例）。
        self.tool_requires("automake/1.18")

    def validate(self):
        # R32: OHOS 与 Linux 同属 Linux-like 平台，必须同时命中。
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # configure.ac 里 PKG_CHECK_MODULES(CACA, caca >= 0.99.beta18) 按**模块名 caca**
        # 查找；libcaca 配方把包拆成 caca/caca++ 两个组件，PkgConfigDeps 默认把组件
        # 命名为 <包名>-<组件名>（实测生成的是 libcaca-caca.pc），于是 configure 报
        # "checking for caca >= 0.99.beta18... no → you need libcaca version 0.99.beta18
        # or later"。PkgConfigDeps 支持用组件的 pkg_config_name 属性覆盖 PC 文件名
        # （pkgconfigdeps.py: comp_name = _get_property("pkg_config_name", dep, comp)），
        # 故把 caca 组件的模块名指回上游模块名，生成 configure 认得的 caca.pc。
        # 必须在 PkgConfigDeps.generate() **之前**设置属性。
        libcaca = self.dependencies["libcaca"]
        if "caca" in libcaca.cpp_info.components:
            libcaca.cpp_info.components["caca"].set_property("pkg_config_name", "caca")
        PkgConfigDeps(self).generate()
        # PKG_CONFIG_PATH 不需要手工注入：AutotoolsToolchain 已把 generators_folder
        # 加进 PKG_CONFIG_PATH（见生成的 conanautotoolstoolchain.sh），指向本配方的
        # generators_folder（build_folder 下），不碰共享 /usr/local（R49/PF6）。
        # VirtualBuildEnv：automake/1.18 的 aclocal/automake 是 perl 脚本，
        # 其模块目录靠包的 buildenv_info 注入 PERL5LIB/ACLOCAL_PATH，只在
        # conanbuild 环境内生效；必须**先** append 再 generate（同 abiword-plugin-* 先例），
        # 否则 conanbuild 环境文件已生成、注入不生效（CI 实测 "aclocal: not found"）。
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        # 本机（HarmonyOS PC, HongMeng Kernel 1.12.0）的 config.guess(2024-07-27)
        # 无法识别该内核，且在 HMDFS 上它 `mkdtemp` 后写 dummy.c 会被拒
        # （E175/E490 家族），configure 因此报
        # "configure: error: cannot guess build type; you must specify one"。
        # 显式给出 build == host 的三元组即跳过 config.guess，且 build 与 host 相同
        # = 保持**本机原生编译**（设备本身即目标机，非交叉），运行期探测不被跳过。
        # conan 只在 build profile != host profile 时自动注入三元组，本任务两侧都是
        # ohos profile，故必须在此显式给（同 archives/m/ming、archives/l/libcaca 先例）。
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()

    def _bootstrap(self):
        """自举 autotools 构建脚本（源码归档不含 configure/Makefile.in）。

        直接跑上游自带的 bootstrap（EXTRA_DIST 成员）：它按 configure.ac 判定需要
        aclocal/autoconf/autoheader/automake，与本项目实际需求一致，比自造命令链更贴合上游。
        用 bash 显式驱动：本机 /bin/sh 可用，但 profile 已把 CONFIG_SHELL/SHELL 定为
        hnp bash（autoconf 的 exec 多位数 fd 重定向、automake 未加引号变量词分割都依赖它）。
        """
        self.run("bash ./bootstrap", env="conanbuild")

    def _relax_umask_in_configure(self):
        """把生成的 configure 里 `umask 077` 改成 `umask 022`（HMDFS 语义）。

        config.status 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录；在
        HMDFS 上该目录实际权限为 2700（drwx--S---），而当前 uid(20020082) 并非文件
        属主、只能靠 file_manager 组位通行，`chmod` 在 HMDFS 上是 no-op（实测
        `chmod 770` 后 ls 仍为 drwx--S---、写入继续 EACCES），于是紧随其后的
        `cat > $tmp/subs1.awk` 报
        "config.status[762]: can't create ./confXXXXXX/subs1.awk: Permission denied /
         config.status: error: could not setup config files machinery"。
        这两行由 autoconf 的 config.status 模板生成、不在源码树内，故只能改生成物
        （同 archives/l/libcaca/0.99.beta20.1 的处理）。断言替换次数以契约变化即失败，
        避免上游/autoconf 改动后静默漏改。
        """
        configure = os.path.join(self.build_folder, "configure")
        with open(configure, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if content.count("umask 077") != 2:
            raise ConanException(
                "umask contract changed in configure: expected 2 occurrences of "
                "'umask 077' (autoconf 2.72 config.status template), got "
                f"{content.count('umask 077')}")
        with open(configure, "w", encoding="utf-8") as f:
            f.write(content.replace("umask 077", "umask 022"))

    def build(self):
        apply_conandata_patches(self)
        self._bootstrap()
        self._relax_umask_in_configure()

        autotools = Autotools(self)
        autotools.configure()
        # FONTDIR：把编译期字体目录指向**包内**真实位置（patches/0001 提供的覆盖点）。
        # 不传就会烤成本机不存在的 `//share/figlet`（conan 用 --prefix=/ + DESTDIR 安装），
        # 运行期报 "error: could not load font pagga"（实测）。
        fontdir = os.path.join(self.package_folder, "share", "figlet")
        autotools.make(args=["-j1", f"FONTDIR={fontdir}"])
        # ── 上游官方完整测试 ──
        # test/Makefile.am: TESTS = check-source check-fonts
        #   check-source: 源码树制表符/行尾空格检查
        #   check-fonts : 用构建出的 toilet 逐个加载 fonts/ 全部字体（24 个）
        # 注意：check-fonts 自己传 `-d ../fonts`（源码树字体），与上面的 FONTDIR 无关。
        autotools.make(target="check")

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # 字体（share/figlet/*.tlf）与 man 页：consumers 需要拿到字体目录
        self.cpp_info.resdirs = ["share", "man"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
