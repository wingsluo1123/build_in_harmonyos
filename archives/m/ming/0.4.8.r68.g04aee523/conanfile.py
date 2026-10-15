#!/usr/bin/env python3
"""Conan recipe for ming (libming) 0.4.8.r68.g04aee523 — Autotools.

libming 是一个用于生成 Macromedia Flash (.swf) 文件的 C 库，随库一同发布
一组 SWF 检查/转码命令行工具（listswf / swfc / swftophp / swftoperl / ...）。

版本号是 git describe 形态：上游 tag `ming-0_4_8` + 68 个提交 + g<sha>
（已用 GitHub compare API 核对 total_commits == 68，与版本号逐位吻合）。

HarmonyOS 适配要点：
  1. 上游归档只带 configure.ac/Makefile.am，不含 autoreconf 生成的 configure；
     而本机与 CI 只有 autoconf 家族，缺 automake/aclocal/libtool（E178），
     因此用 tool_requires 拉入 automake + libtool，在 build() 内 autoreconf 自举。
  2. 语言绑定（perl/php/python/tcl）全部显式关闭：它们是可选子工程，不属于
     C 库的功能契约；本机无 php/phpize，--enable-php 会让 configure 直接报错。
  3. 媒体可选库经 Conan 依赖启用。上游 configure 对 freetype 是**默认开启**且
     找不到 freetype2 即 AC_MSG_ERROR；zlib/libpng/giflib 由 AC_CHECK_LIB 自动
     探测，不声明则静默禁用，会导致 SWF 压缩与 PNG/GIF 位图功能缺失，并使上游
     测试套件中 10 条以 GIF/PNG/FREETYPE 为门槛的用例被跳过。

License: LGPL-2.1-or-later（上游 LICENSE / LICENSE_GPL2）
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import copy, export_conandata_patches, get, apply_conandata_patches, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class MingConan(ConanFile):
    name = "ming"
    version = "0.4.8.r68.g04aee523"
    description = ("libming — SWF (Macromedia/Adobe Flash) authoring library, "
                   "plus the SWF inspection and transcoding utilities")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libming/libming"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # freetype：上游 configure 默认开启，缺 freetype2 即报错（PKG_CHECK_MODULES）
        self.requires("freetype/2.14.3.2.1")
        # 以下三项由 configure 的 AC_CHECK_LIB 自动探测：不声明则静默禁用
        # zlib 版本跟随 libpng/1.6.58.3 的要求（1.3.2），否则图上版本冲突
        self.requires("zlib/1.3.2")
        self.requires("libpng/1.6.58.3")
        self.requires("giflib/5.2.2")

    def build_requirements(self):
        # E178：宿主/CI 只有 autoconf 家族，缺 automake/aclocal/libtool；源码包又
        # 不含生成的 configure，必须自举，故以 tool_requires 补齐（同 afuse 做法）。
        # tool_requires 按 build profile 解析，conan create 需同时传 -pr:h 与 -pr:b。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # freetype 经 PKG_CHECK_MODULES(freetype2) 探测 → 需要生成 .pc
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # configure.ac 用 AC_ARG_ENABLE 声明绑定开关，默认全关；这里显式关闭，
        # 避免宿主上恰好存在的解释器（本机有 perl）让绑定被意外构建。
        tc.configure_args.append("--disable-perl")
        tc.configure_args.append("--disable-php")
        tc.configure_args.append("--disable-python")
        tc.configure_args.append("--disable-tcl")
        # E007：OHOS 上 config.guess 有两个问题——(1) uname -s = HarmonyOS 不在其
        # 已知系统表中；(2) 本平台 HMDFS 安全限制让它写不了探针临时文件
        # （实测 config.guess: can't create .../dummy.c: Permission denied），
        # 两条都导致 "cannot guess build type" 而中断。故直接给出三元组，让
        # configure 完全不调用 config.guess。
        # 取值 aarch64-unknown-linux-gnu：automake 1.18 自带的 config.sub 实测只
        # 接受该形态（aarch64-linux / *-linux-ohos / *-linux-musl 均被拒）。
        # build == host → autoconf 按 native 处理（cross_compiling=no），因此不存在
        # E007 所警告的"交叉误判→AC_RUN_IFELSE 全跳过→config.h 错误"；libming 的
        # configure.ac 本身也不含 AC_RUN_IFELSE/AC_TRY_RUN（已核对，仅 AC_C_BIGENDIAN）。
        # 同 a52dec/0.7.4 先例。
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # 上游 src/actioncompiler 用 flex(-Pswf4/-Pswf5) + bison 生成词法/语法器，
        # 两边各自产生一份暂定定义 swf4debug/swf5debug（lex.swf4.c 与
        # swf4compiler.tab.c）。clang 11+ 默认 -fno-common，暂定定义变为强符号 →
        # "ld.lld: error: duplicate symbol: swf4debug/swf5debug"。加 -fcommon 恢复
        # 传统 common 符号合并语义（ant-phone/0.2.1 同因同治，仓库 79 个配方先例）。
        tc.extra_cflags.append("-fcommon")
        # pkg.m4（提供 PKG_CHECK_MODULES）随 hnp 的 pkg-config 安装发布，autoreconf
        # 的 aclocal 必须能找到它。经 toolchain 环境注入——recipe 自身的
        # buildenv_info 不会作用于自己的构建环境（afuse 配方同一结论）。
        env = tc.environment()
        # 依赖 include/lib 注入：libming 的 configure 用 AC_CHECK_HEADERS(gif_lib.h)
        # 与 AC_CHECK_LIB(png|gif|z) 探测可选库，读的是 CPPFLAGS/LDFLAGS；而
        # AutotoolsToolchain 生成的环境里不含依赖路径（实测生成的
        # conanautotoolstoolchain.sh：CPPFLAGS 只有 -DNDEBUG、LDFLAGS 为空），
        # 不注入会把 libpng/giflib 静默判成"不存在"→ PNG/GIF 位图功能丢失、
        # 上游 4 条用例被跳过。注意 zlib 之所以"探测到"是命中了系统自带的
        # libz/zlib.h，并非 Conan 依赖，不能据此认为注入已生效。
        for dep in self.dependencies.host.values():
            comp = dep.cpp_info.aggregated_components()
            for inc in comp.includedirs:
                env.append("CPPFLAGS", f"-I{inc}")
            for lib in comp.libdirs:
                # 同一处注入两件事：-L 供链接期、-Wl,-rpath 供运行期。
                # 运行期搜索路径必须写进 ELF 的 RUNPATH：本平台上 LD_LIBRARY_PATH
                # 在 make → sh → perl → libtool wrapper → 测试程序 这条子进程链路上
                # 不可靠（实测同一命令在交互 shell 里生效、经 make 链执行失效，报
                # "Error loading shared library libpng16.so.16 / libgif.so.7"）。
                # 注意：不能走 AutotoolsToolchain.extra_ldflags —— 在
                # tc.generate(env=<自定义 env>) 路径下它不会进 LDFLAGS（实测生成脚本
                # grep rpath 命中 0），而本 env.append 注入的 -L 确实生效。
                env.append("LDFLAGS", f"-L{lib} -Wl,-rpath,{lib}")
                env.append_path("LD_LIBRARY_PATH", lib)
        for _d in sorted(glob.glob("/data/service/hnp/*/*/share/aclocal")):
            env.append_path("ACLOCAL_PATH", _d)
        tc.generate(env=env)

    def build(self):
        os.umask(0)
        apply_conandata_patches(self)

        # 上游归档不含 configure（autoreconf 产物不入版本库）→ 自举
        self.run("autoreconf --install --verbose", cwd=self.source_folder)

        # E114：生成的 configure 里 `tmp=`(umask 077 && mktemp -d "./confXXXXXX")``
        # 在 HMDFS 上产出 drwx--S--- 权限目录，连 owner 也写不进去（chmod 同样无效），
        # 于是 config.status 报 "./confXXXXXX/subs1.awk: Permission denied" →
        # "could not setup config files machinery"（实测）。把 umask 放宽为 000 即可
        # （同 afuse / abiword 配方做法；configure 是本步骤 autoreconf 现场生成的产物）。
        self.run("sed -i 's/umask 077/umask 000/g' configure", cwd=self.source_folder)

        autotools = Autotools(self)
        autotools.configure()
        # R9：OHOS 上并行构建受限，统一 -j1
        autotools.make(args=["-j1"])
        # 上游官方测试：每个用例编译 C/C++ 程序生成 .swf，再由 test/dotests.pl
        # 调 util/listswf 转储并与同名 .ref 逐行 diff 比对。
        # 运行期必须能找到依赖包的 .so：OHOS loader 不搜索 conan 缓存目录，否则
        # make check 里刚构建的测试程序（及它加载的 libming.so）报
        # "Error loading shared library libpng16.so.16 / libgif.so.7"
        # → png_*/DGif* 全部 symbol not found，用例全灭（实测）。
        # 这里在命令上显式前置依赖 lib 目录（两种"写进环境脚本"的方式——toolchain
        # env 注入、run(env="conanbuild")——在该调用点实测均未生效，显式前置是
        # 确定性做法，E019 set-ld-library-path）。
        lib_dirs = ":".join(
            lib
            for dep in self.dependencies.host.values()
            for lib in dep.cpp_info.aggregated_components().libdirs
        )
        env_prefix = ('LD_LIBRARY_PATH="' + lib_dirs
                      + '${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ')
        self.run(env_prefix + "make check", cwd=self.build_folder,
                 env="conanbuild")

    def package(self):
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        # libtool 归档（.la）对 Conan 消费者无用且内嵌绝对路径，统一删除
        # 注意：ADAPTATION_GUIDE 模板里的 copy(..., delete=True) 在 Conan 2.29
        # 已不支持（TypeError: unexpected keyword argument 'delete'），须用 rm。
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["ming"]
        # 上游随库安装命令行工具（listswf/swfc/swfto* 等），产物含 bin/
        # → 软件级 commands.json 声明（R38）
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
