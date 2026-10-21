#!/usr/bin/env python3
"""Conan recipe — xshogi 1.4.2 (GNU Shogi 的 X11/Athena 图形前端)

上游: https://ftp.gnu.org/gnu/gnushogi/xshogi-1.4.2.tar.gz （GNU 官方发布包）
       configure.ac:8 AC_INIT([xshogi],[1.4.2],...) 与任务版本逐字一致。
许可证: 分发包内 COPYING 为 GNU GPL v3 全文。

构建系统: autotools（configure + make）。tarball 已带预生成的
configure / Makefile.in / config.h.in / parser.c / scanner.c / parser.h，
因此不需要 autoreconf，也不需要 yacc/lex（BUILT_SOURCES=parser.h 的生成物
比 parser.y 新，make 不会重建）。

X 探测（configure.ac 的 AC_PATH_XTRA）: CI/真机既无 xmkmf，也没有系统 X11 树
（实测 /lib、/lib64、/usr/lib、/system/lib*、$HOME/usr/local/lib 下均无
libX11*/libXaw*），因此预置 autoconf 缓存变量 ac_cv_have_x="have_x=yes"
跳过 xmkmf 探测与目录猜测。真正的头文件/库路径全部由 Conan 依赖提供
（AutotoolsDeps 生成 CPPFLAGS/LDFLAGS/LIBS，经 conanbuild 环境注入），
不写死任何系统前缀（R26/R49）。

链接: 上游 Makefile.am xshogi_LDADD = @X_LIBS@ -lXaw -lXmu -lXt -lXext -lX11。
have_x=yes 且未传 --x-includes/--x-libraries 时 @X_LIBS@ 为空，五个 X 库由
AutotoolsDeps 注入的 LIBS 提供（libxaw/libxmu/libxt/libxext/libx11 均为
ohpcd 已发布的 OHOS/armv8 二进制，另有传递依赖 libxpm/libsm/libice/libxcb/
libxau/libxdmcp）。运行期设备无系统 X11 .so，依赖由 Conan 依赖链提供，
package_info() 已把各依赖 libdir 注入 runenv 的 LD_LIBRARY_PATH。

平台适配补丁 patches/0001-add-version-option.patch: main() 中在
XtAppInitialize 之前对 -version/--version 早退（打印版本并 exit(0)）。
理由见 conandata.yml 与 notes.md —— libXt/Xt 都不实现 -version，无头环境
下上游命令行选项全部会先撞 XOpenDisplay 失败。

上游测试: 无自动化测试套件（源码包无 tests/ 目录，Makefile.am 无
TESTS/check_PROGRAMS/check-local），清点证据见 test_package/MANIFEST.yml。
build() 仍调用 automake 的 check 目标留证（空套件）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XshogiConan(ConanFile):
    name = "xshogi"
    version = "1.4.2"
    description = ("XShogi — X11/Athena (Xt/Xaw) graphical front-end for the "
                   "GNU Shogi Japanese chess engine")
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gnushogi/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # X11 依赖链（全部为 ohpcd 已发布的 OHOS/armv8 二进制）。
        # libxmu/libxext 的 OHOS 包把 libx11 钉在 1.8.13（force），libx11 显式
        # 用 override 统一，避免与传递依赖产生版本分裂（xpaint/xeyes 同款修法）。
        self.requires("xorgproto/2025.1", transitive_headers=True)
        self.requires("libx11/1.8.13", override=True,
                      transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0.1",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libxt/1.3.1",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libxmu/1.3.1.1",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libxaw/1.0.14",
                      transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xshogi supports Linux and OHOS, not {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # 运行期自包含：package() 把各依赖 .so 复制到 lib/，链接期用
        # DT_RPATH=$ORIGIN/../lib 让 bin/xshogi 在包内找库（myman 4.0.116
        # / accessibility 同款 layout）。
        # 两层转义（每层都实测过）：
        #   1) conan 生成的 export LDFLAGS="..."（双引号）→ 值里必须写
        #      \$\$ORIGIN，sourcing 后 LDFLAGS 才是 -Wl,-rpath,'$$ORIGIN'；
        #   2) Makefile 里 LDFLAGS 是递归变量（LDFLAGS = ...），make 展开
        #      $(LDFLAGS) 时会把 $$ORIGIN 折叠成 $ORIGIN —— 若写成单个 $
        #      make 会把 $O 当成未定义变量吃掉，实测得到 DT_RPATH=[RIGIN]；
        #   3) 最后 sh 解析 recipe 行，字面单引号保住 $ORIGIN 不被展开。
        # 必须在 tc.environment() 之前 append：environment() 会快照
        # self.ldflags（autotoolstoolchain.py:308），之后再 append 不生效。
        tc.extra_ldflags.append("-Wl,-rpath,'\\$\\$ORIGIN/../lib'")
        # musl 的 loader 对 DT_RUNPATH 支持有限，统一用旧式 DT_RPATH
        tc.extra_ldflags.append("-Wl,--disable-new-dtags")
        env = tc.environment()
        # 跳过 AC_PATH_XTRA 的 xmkmf 探测与目录搜索：CI/真机无 xmkmf、
        # 无系统 X11 树。after this, x_includes/x_libraries 保持空，
        # X_CFLAGS/X_LIBS 为空，路径全部来自 AutotoolsDeps。
        env.define("ac_cv_have_x", "have_x=yes")
        # AC_PATH_XTRA 会把 X_LIBS 里的 -lXaw/-lX11/... 一起写进 conftest 的
        # 链接行（config.log 实证：-lXaw6 -lXaw7 -lXmuu -lXmu -lXpm -lXext
        # -lXt -lX11 -lxcb -lSM -lXdmcp -lXau -lICE），configure 随后要
        # 直接运行 ./conftest；设备没有系统 X11 动态库，loader 找不到这些
        # DT_NEEDED → "Error loading shared library libXaw.so.7" → configure
        # 报 "cannot run C compiled programs"。把各依赖 libdir 加入构建环境
        # 的 LD_LIBRARY_PATH（vigor 0.016 同款修法）。
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.aggregated_components().libdirs or []:
                env.append_path("LD_LIBRARY_PATH", libdir)
        tc.generate(env=env)

    def _fix_configure_for_hmdfs(self):
        """E011：HMDFS 上 `umask 077 && mktemp -d "./confXXXXXX"` 建出的临时目录
        是 mode 02700（setgid、drwx--S---），当前进程无法在其中创建文件，
        config.status 随即报 "./confXXXXXX/subs1.awk: Permission denied" /
        "could not setup config files machinery"。

        设备实测（同一 conan 构建目录内）：
          umask 077 + mktemp -d → drwx--S--- 不可写
          umask 022 + mktemp -d → drwxr-s--x 可写
          umask 002 + mktemp -d → drwxrws--x 可写
        故按 E011（rec_command: sed -i 's/umask 077/umask 022/g' configure）
        就地改写 configure。configure 是 autoconf 生成文件，refresh-patch 会
        把它判为生成文件跳过，因此沿用既有做法（xeyes 1.3.1 / 4ti2 1.6.10.1 /
        abiword-plugin-clarisworks 3.0.8）在 build() 内改写；改动只落在构建
        缓存中的 source_folder，不进仓库、不改变非 OHOS 平台行为。
        """
        if self.settings.os != "OHOS":
            return
        path = os.path.join(self.source_folder, "configure")
        with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
            data = f.read()
        if "umask 077" not in data:
            self.output.warning(
                "E011: configure 中未找到 'umask 077'（上游文本已变化？）")
            return
        with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
            f.write(data.replace("umask 077", "umask 022"))

    def build(self):
        apply_conandata_patches(self)
        self._fix_configure_for_hmdfs()
        # E490：HarmonyOS 适配路径可能丢失脚本可执行位。configure 由 autoconf
        # 生成、install-sh/missing/compile/depcomp/ylwrap 由 automake 提供，
        # 都需要 +x 才能被 configure/Makefile 调用。chmod 只改权限、不改内容。
        for script in ("configure", "install-sh", "missing", "compile",
                       "depcomp", "ylwrap"):
            path = os.path.join(self.source_folder, script)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # 上游无测试套件；仍执行 automake 的 check 目标留证（空套件）
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 运行期自包含（设备实测无系统 X11 .so：/lib、/lib64、/usr/lib、
        # /system/lib*、$HOME/usr/local/lib 均无 libX11*/libXaw*）。
        # 把各依赖的 .so 按文件名（=SONAME）复制到 lib/，配合链接期
        # DT_RPATH=$ORIGIN/../lib 让 bin/xshogi 在包内寻库。
        # 放 lib/ 而不是 bin/：bin/ 只留真正的可执行文件（CI L2 smoke 会逐个
        # 执行 bin/ 下文件，混入 .so 会刷出上百条无意义的 "failed" 明细），
        # 且 .so 归 lib/ 也符合 L5 的 SONAME 检查位置。
        # HMDFS 不跟踪 symlink（E050），符号链接一律解引用后拷实体内容。
        lib_dir = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.aggregated_components().libdirs or []:
                if not libdir or not os.path.isdir(libdir):
                    continue
                for name in sorted(os.listdir(libdir)):
                    if ".so" not in name:
                        continue
                    src = os.path.join(libdir, name)
                    if os.path.islink(src):
                        src = os.path.realpath(src)
                    if not os.path.isfile(src):
                        continue
                    dst = os.path.join(lib_dir, name)
                    if not os.path.exists(dst):
                        shutil.copy2(src, dst)

    def package_info(self):
        self.cpp_info.includedirs = []
        # 应用包：lib/ 只放运行期依赖，不作为链接接口对外暴露
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        # 自包含：包内 lib/ 优先于依赖包目录
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.aggregated_components().libdirs or []:
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
