#!/usr/bin/env python3
"""Conan recipe — libappindicator 12.10.1 (HarmonyOS PC, aarch64/OHOS).

libappindicator 让应用把托盘图标 + 菜单导出到 Application Indicators
（StatusNotifierItem）区域。上游构建系统为 autotools（GTK3 路径产出
libappindicator3.so + appindicator3-0.1.pc）。

HarmonyOS PC 适配要点（详见 notes.md，均有本地实测/知识库依据）：

  1. 源码身份：上游 Launchpad 从未发布 12.10.1 的 release tarball（12.10 系列
     官方下载只有 12.10.0）。12.10.1 是 12.10 分支的维护快照，发行版统一以
     Ubuntu orig tarball `libappindicator_12.10.1+20.10.20200706.1.orig.tar.gz`
     分发（NixOS/Fedora 同源）。详见 conandata.yml 注释。
  2. 随包交付 libdbusmenu 16.04.0（R49 私有 prefix）：上游 configure.ac 硬依赖
     `dbusmenu-gtk3-0.4 >= 0.5.90`，而制品仓未发布 libdbusmenu（`conan list
     "*dbusmenu*/*" -r ohpcd` 实测为空）。按「一库一 PR / 禁止捎带」（PF1/R36）
     不能在本 PR 新增独立包，故把官方 libdbusmenu 16.04.0 构建进
     `build_folder/prefix`（R49：CPPFLAGS/LDFLAGS/PKG_CONFIG_PATH 全部只指向
     该私有 prefix，绝不写 /usr/local 等共享位置），并将其运行库/头文件/.pc
     随本包交付，使上游测试源码（内含 <libdbusmenu-glib/*.h>）可直接消费。
  3. glib 版本统一为 gtk 链的 2.84.0.1（force）：制品仓的 glib 2.88.0 与
     gtk/3.24.43 链 pin 的 2.84.0.1 若并存，PkgConfigDeps 会生成同名 .pc
     （glib-2.0.pc 等）互相覆盖（E524 同类，libayatana-appindicator-glib 2.0.3
     先例同样强制统一）。上游 configure.ac 的 TESTDEPS（dbus-glib-1）探测用
     0003 补丁改为非致命：dbus-glib/0.114 锁定 glib/2.88.0，实测按其配方对
     glib 2.84 源码重建失败（ld.lld 找不到 -lgio-2.0/-lffi）→ tests/ 中使用
     dbus-glib 的 6 个程序不编译（它们同时依赖 Xvfb + dbus-test-runner，
     OHOS 平台本就不可运行）。
  4. autoreconf 所需宏/工具在 OHOS 构建镜像缺失：gtk-doc.m4（GTK_DOC_CHECK）、
     vala.m4（AM_PROG_VALAC）都不存在，autoreconf 直接失败 → 0001 补丁移除这
     两个宏并停建 docs/（0002 补丁从 SUBDIRS 去掉 docs）。随包 libdbusmenu 的
     预生成 configure 硬要求 intltool/gettext/perl/XML::Parser → 0004 补丁在
     配置期把这五处探测改宽松，并在 --disable-tests 时补 HAVE_VALGRIND 条件
     定义（否则 conditional "HAVE_VALGRIND" was never defined）。补丁不触碰
     src/ 与 tests/，上游测试用例零修改。
  5. config.sub 不认识 `linux-ohos`（autoreconf 从构建机 automake 复制，版本随
     构建机变化，无法用稳定 .patch 打，且**结构本身**也随版本变——CI #92718 实测：
     CI 的 conan automake/1.18 装出 2024-05-27 版，白名单已是每行一项的
     `| gnu* \ …` 列表、旧的单行 `gnu* | android* | bsd*` 不存在，严格替换直接
     报 replace_in_file 未命中；而该版上游**已内置** `| ohos*` 与
     `linux-ohos*-`，根本无需注入。故 build() 按结构分支：老版（单行白名单，
     如系统 automake 1.16 的 2022-01-03 版）按 E007 同时补两张白名单（基本
     系统类型加 `ohos*`、kernel-os 配对加 `linux-ohos*`，只补前者仍报 Kernel
     `linux' not known to work with OS `ohos'`）；新版（已含 ohos）跳过注入。
     两种结构最后都用**真执行 config.sub aarch64-linux-ohos** 做 fail-closed
     行为校验；同时按 E114/E236 把生成的 configure 里 `umask 077` 改成
     `umask 022`（HMDFS 拒绝 umask 077 下自建临时目录）。
  6. 构建/打包卫生（均有实测故障与知识库先例，见 notes.md 问题 9-15）：
     依赖包 `*.la` 记录发布机构建前缀 → 构建前重定位 libdir 并清空
     dependency_libs（否则 libtool 拼出 `//lib/libfreetype.la` 死路径）；
     上游把 app-indicator-enum-types.h 同时列进两组 HEADERS → `make install -j1`
     避免并行装同一目标；发布的 .so 由 libtool 写入构建机 DT_RUNPATH → 打包时
     用 patchelf --remove-rpath 清除（必须在 ELF 签名之前）；包内 .pc 的 prefix
     统一改写为 `${pcfiledir}/../..` 以便重定位。
  7. CI worker 是 HarmonyOS PC（原生构建，cross_building=False）：此时
     AutotoolsToolchain 不注入 --build/--host，configure 只能调 config.guess，
     而 OHOS 的 `uname -s` 返回 "HarmonyOS" → CI #65065 实测
     `configure: error: cannot guess build type; you must specify one`（失败点
     是随包 libdbusmenu 那个 2015 版 config.guess）。故对随包 libdbusmenu 始终
     显式给 `*-linux-gnu` 三元组，主包在原生构建时补同款三元组（交叉构建时
     toolchain 自己注入 `--host=aarch64-linux-ohos --build=x86_64-linux-gnu`，
     本地验证行为不变）。
"""
import glob
import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    mkdir,
    replace_in_file,
    rm,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibappindicatorConan(ConanFile):
    name = "libappindicator"
    version = "12.10.1"
    description = ("Application Indicators library: export a tray icon and a "
                   "D-Bus menu (com.canonical.dbusmenu) from GTK3 applications "
                   "(12.10.1 maintenance snapshot).")
    license = "LGPL-2.1-or-later"
    homepage = "https://launchpad.net/libappindicator"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {
        "shared": True,
        "fPIC": True,
        "glib/*:shared": True,
        "gtk/*:shared": True,
    }
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def build_requirements(self):
        # 上游 tarball 不含预生成的 configure（autoreconf 产物不进发行包），
        # build() 必须 `autoreconf -fi -I m4` 自举。CI worker（HarmonyOS PC 原生
        # 构建）的基础 PATH 只有
        # `/data/app/bin:/system/bin:/system/sbin:/vendor/bin`，**没有 aclocal**
        # （实测 CI #65510：`sh: aclocal: inaccessible or not found` →
        # `autoreconf: error: aclocal failed with exit status: 127`）；本地 WSL
        # 交叉构建机则自带 autotools（/usr/bin/{aclocal,automake,autoreconf}）。
        # 因此**仅在缺工具时**才 tool_requires（同 xsel/1.2.1、afuse、
        # argp-standalone 处理 E178 的思路）——无条件引入会把 autoconf 及其
        # 依赖 m4 拉进交叉构建（m4 的 printf-frexpl 在 OHOS 交叉下编译失败，
        # 实测），白白拖垮本地验证路径。
        #
        # ★ autoconf 单独拆出来按"真没有 autoreconf 才引入"判定（2026-10-15，
        #   修 CI #90942/#91201/#91638/#92068 同一失败链）★
        # 实测失败链：`autoreconf` 实际执行的是 HNP 的
        #   /data/service/hnp/bin/autoreconf（系统 perl 5.42.0），而
        #   `tool_requires("autoconf/2.72")` 会把 conan `perl/5.42.2` 拉进
        #   build 图（conan graph info 实测：automake+libtool 单独在图时无
        #   perl 节点；加 autoconf/2.72 后出现 perl/5.42.2 与 m4），perl 包的
        #   buildenv 把 PERL5LIB 指向 conan perl 的 lib/perl5 全套目录 →
        #   系统 perl 跑 autoreconf 时 `require Cwd` 命中 conan perl 5.42.2
        #   的 XS（Cwd.so，包内 0750 属主 20001006）→ `Permission denied`/
        #   ABI 冲突 → `ConanException: Error 255`。
        # 已合入 main 的 irqbalance/1.9.4 同环境先例：不 tool_require autoconf，
        # 复用 HNP 自带 autoconf 2.72 + 系统 perl 5.42.0（见其 build() 注释）。
        # 本地/PC 无 HNP 的机器仍回退 conan autoconf（此时 autoreconf 的
        # shebang 与 PERL5LIB 同指 conan perl，自洽可用）。
        if not self._host_has_autotools():
            self.tool_requires("automake/1.18")
            self.tool_requires("libtool/2.5.4")
        if not self._host_has_autoreconf():
            self.tool_requires("autoconf/2.72")

    @staticmethod
    def _host_has_autotools():
        """构建机上是否已有 autotools 全家桶（aclocal/automake/libtoolize）。"""
        return all(
            shutil.which(tool)
            for tool in ("aclocal", "automake", "libtoolize")
        )

    @staticmethod
    def _host_has_autoreconf():
        """是否有可用的 autoreconf：PATH 中优先，其次 HNP 自带（CI worker）。

        CI worker 的基础 PATH 里没有 autoreconf，但 /data/service/hnp/bin 下有
        （autoconf 2.72 + 系统 perl 5.42.0），build() 时 conanbuild 会把该目录
        加进 PATH——此时不能再 tool_require conan autoconf，否则 perl/5.42.2
        进图污染 PERL5LIB（见 build_requirements 注释）。
        """
        return bool(shutil.which("autoreconf")) or os.path.isfile(
            "/data/service/hnp/bin/autoreconf"
        )

    @property
    def _private_prefix(self):
        """R49：随包构建的依赖只进 build_folder 私有 prefix。"""
        return os.path.join(self.build_folder, "prefix")

    def requirements(self):
        # 与 gtk 链统一 glib 版本（见模块 docstring 第 3 点）。
        # 注：不引入 dbus-glib —— 上游 configure.ac 的 TESTDEPS 探测已用
        # 0003 补丁改为非致命：制品仓的 dbus-glib/0.114 锁定 glib/2.88.0，
        # 与本链 glib/2.84.0.1 冲突；实测按其配方对 glib 2.84 源码重建会失败
        # （ld.lld: unable to find library -lgio-2.0/-lffi，见 notes.md）。
        # tests/ 中仅 6 个使用 dbus-glib 的程序因此不编译（它们本身也需要
        # Xvfb + dbus-test-runner，OHOS 平台不可运行）。
        self.requires(
            "glib/2.84.0.1",
            transitive_headers=True,
            transitive_libs=True,
            options={"shared": True},
            force=True,
        )
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        # 头闭包补全：gtk/gtk.h → gdk/gdk.h → pango/pango.h → pango-coverage.h
        # 直接 `#include <hb.h>`，而制品仓的 pango/1.50.14.1.1 配方未对
        # harfbuzz 声明 transitive_headers → 消费方编译 gtk.h 时报
        # "fatal error: 'hb.h' file not found"（实测）。这里显式带上。
        self.requires(
            "harfbuzz/14.2.0.1.1.1", transitive_headers=True, transitive_libs=True
        )

    # ------------------------------------------------------------------ source
    def source(self):
        get(
            self,
            **self.conan_data["sources"]["libappindicator"],
            strip_root=False,
            destination=self.source_folder,
        )
        get(
            self,
            **self.conan_data["sources"]["libdbusmenu"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "libdbusmenu-src"),
        )

    # ---------------------------------------------------------------- generate
    def generate(self):
        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        self._provide_missing_glib_pcs()
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.append("--with-gtk=3")
        # 上游默认即构建 tests/（WANT_TESTS 默认 yes），显式声明以便审查可见。
        toolchain.configure_args.append("--enable-tests")
        # CI worker 是 HarmonyOS PC（原生构建 → cross_building=False，实测 CI
        # #65065）：AutotoolsToolchain 此时**不注入** --build/--host，configure
        # 只能调 config.guess，而 OHOS 的 `uname -s` 返回 "HarmonyOS" →
        # `configure: error: cannot guess build type; you must specify one`。
        # 故仅在原生构建时显式补 GNU 三元组（交叉构建时 toolchain 自己会注入
        # `--host=aarch64-linux-ohos --build=x86_64-linux-gnu`，本地 qemu 验证
        # 路径行为保持不变）。
        if not cross_building(self):
            triplet = self._gnu_triplet(self.settings)
            toolchain.configure_args.extend(
                [f"--build={triplet}", f"--host={triplet}"]
            )
        toolchain.generate()
        self._inject_autotools_buildenv()

    def _inject_autotools_buildenv(self):
        """向 conanbuild 注入 aclocal/autoreconf 所需环境（仅当 automake 是
        tool_requires 依赖时；本机自带 autotools 则完全不干预）。

        与已合入 main 的 irqbalance/1.9.4 的 generate() 同法：
          * PERL5LIB 只指向 automake 包自己的 share/automake-1.18（纯 Perl
            模块目录）。aclocal 实际是 HNP perl 跑的 perl 脚本，需要
            Automake::* 模块；但**绝不能**让 PERL5LIB 混入 conan perl 的
            lib/perl5（5.42.2 的 XS，如 Cwd.so）——那是 CI #92068 失败链的
            根因（见 build_requirements 注释）。
          * ACLOCAL_PATH 覆盖 libtool/pkgconf/automake 的 aclocal 宏目录，
            避免 aclocal 在 HNP 缺宏时失败。
          * _lt_pkgdatadir 指向 conan libtool 的 share/libtool，libtoolize
            找不到自身数据文件时使用。
        """
        build_deps = {
            dep.ref.name: dep for _, dep in self.dependencies.build.items()
        }
        am = build_deps.get("automake")
        if am is None:
            # 本机自带 autotools（本地 WSL 交叉构建路径），环境保持原样。
            return
        be = self.buildenv_info
        am_share = os.path.join(am.package_folder, "share")
        perl5lib = os.path.join(am_share, "automake-1.18")
        aclocal_dirs = [
            os.path.join(am_share, "aclocal"),
        ]
        lt = build_deps.get("libtool")
        if lt is not None:
            lt_share = os.path.join(lt.package_folder, "share")
            aclocal_dirs.append(os.path.join(lt_share, "aclocal"))
            lt_m4 = os.path.join(lt_share, "m4")
            if os.path.isdir(lt_share) and not os.path.exists(lt_m4):
                try:
                    os.symlink("../aclocal", lt_m4)
                except OSError:
                    pass
            be.define("_lt_pkgdatadir", lt_share)
        # PERL5LIB 只在**没有** conan autoconf/perl 时才由我们接管：本机无
        # HNP 时会回退 tool_requires autoconf/2.72（见 build_requirements），
        # 此时 autoreconf 用的就是 conan perl，其 PERL5LIB 必须保持 conan
        # 自己的全套目录，不能被裁剪成 automake-only（否则 conan autoreconf
        # 找不到 autoconf 的 Perl 模块）。CI worker 有 HNP → 图里无 perl →
        # 这里 define 的 automake-only 值即为唯一值，正是要的效果。
        if "autoconf" not in build_deps:
            be.define("PERL5LIB", perl5lib)
            self.output.info(f"[autotools-env] PERL5LIB={perl5lib}")
        be.define("ACLOCAL_PATH", os.pathsep.join(aclocal_dirs))
        self.output.info(
            f"[autotools-env] ACLOCAL_PATH={os.pathsep.join(aclocal_dirs)}"
        )

    @staticmethod
    def _gnu_triplet(settings):
        """conan settings → **老版 config.sub 也认** 的 GNU 三元组。

        libdbusmenu 16.04.0 自带 2015-08-20 版 config.guess/config.sub：
        ① CI worker（HarmonyOS PC）上 config.guess 直接
        `unable to guess system type`（uname -s = HarmonyOS）→
        `configure: error: cannot guess build type; you must specify one`
        （实测 CI #65065 失败点即 `_build_libdbusmenu()` 的 configure）；
        ② 该版 config.sub 也不认 `ohos` OS。
        故对随包 libdbusmenu 统一使用 `*-linux-gnu` 三元组（与制品仓
        xprop/1.2.8、xauth/1.1.4 处理 E007 的做法一致），目标平台由 toolchain
        注入的 CC/CXX/CFLAGS 决定，与三元组本身无关。
        """
        arch = {
            "armv8": "aarch64",
            "armv7": "armv7",
            "x86_64": "x86_64",
        }.get(str(settings.arch), str(settings.arch))
        return f"{arch}-linux-gnu"

    def _libdbusmenu_triplets(self):
        """返回随包 libdbusmenu 的 `(--build, --host)`，**保证二者不相等**。

        ================== CI #90732 静默 rc=1 的真根因（本地已复现）==================
        历史症状：`_build_libdbusmenu()` 的 configure 在**零输出**（stdout 1111 B、
        stderr 0 B）的情况下直接 rc=1，无从下手。之前两轮把方向误判为 intltool
        探测（提交 ddb6c0a5 为此加了 fail-closed 守卫），实测守卫**放行**了，
        configure 依旧 rc=1 —— 说明 intltool 根本不是原因。

        本地用同一 tarball + 同一补丁序列复现后，`bash -x` 抓到真凶：

            configure:4190: error: in `/…/build':
            configure:4192: error: cannot run C compiled programs.
            If you meant to cross compile, use `--host'.
            See `config.log' for more details

        机制（autoconf 语义，已逐条实测）：
          * `--build=<X> --host=<X>`（**两者相同**）⇒ autoconf 判定为**原生构建**，
            于是 `cross_compiling` 停在 `no`/`maybe`，configure 坚持要**运行**
            刚链接出来的 conftest；
          * CI worker 上 conan `settings` 与 `settings_build` 的 arch **同为
            armv8**，而 `_gnu_triplet()` 只看 arch ⇒ 两边都被映射成
            `aarch64-linux-gnu` ⇒ 命中上面这条原生判定；
          * 但工具链是 OHOS 目标（`os=OHOS`，clang wrapper 指向 aarch64-ohos），
            链出的 conftest 在 worker 上根本执行不了 ⇒ as_fn_error ⇒ rc=1；
          * 该错误在 dash 下**不留 stderr**，于是表现为"静默 rc=1"。

        实测对照（同一环境，唯一变量是三元组）：
            --build=aarch64-linux-gnu --host=aarch64-linux-gnu  → rc=1，卡在
                "checking whether we are cross compiling... "（无 result）
            --build=x86_64-pc-linux-gnu --host=aarch64-linux-gnu → 越过该检查，
                一路走到 `checking for DBUSMENUGTK...`（即正常进入依赖探测）

        修法：`--build` 用**真实构建机**三元组（`config.guess` 语义：arch 取自
        `settings_build`，但 **os 恒为 linux-gnu**——因为随包 2015 版 config.sub
        不认 `ohos`，实测 `--host=aarch64-linux-ohos` 会停在
        "checking host system type... " 静默 rc=1），`--host` 用目标三元组。
        两者 arch 相同时也**必须**区分开——这正是 CI worker 的情形；此时把
        `--build` 落到 `x86_64-linux-gnu`（CI worker 的宿主是 x86_64，见
        `settings_build`），从而强制 autoconf 走交叉分支、不再尝试运行 conftest。

        注意：目标平台仍由 toolchain 注入的 CC/CXX/CFLAGS 决定，与三元组本身无关
        （与制品仓 xprop/1.2.8、xauth/1.1.4 处理 E007 的做法一致）。
        """
        host_triplet = self._gnu_triplet(self.settings)
        build_triplet = self._gnu_triplet(self.settings_build)
        if build_triplet == host_triplet:
            # build 与 host 撞车 ⇒ autoconf 会当原生构建设法运行 conftest（见
            # docstring）。此时把 --build 固定为 x86_64-linux-gnu：CI worker 与
            # 本地验证机都跑在 x86_64 宿主上（conan settings_build.arch=x86_64），
            # 且该串必被随包 2015 版 config.sub 接受。
            self.output.info(
                "libdbusmenu: --build 与 --host 均为 "
                f"{host_triplet}，强制 --build=x86_64-linux-gnu 以避免 autoconf "
                "误判为原生构建（否则 configure: cannot run C compiled programs）"
            )
            build_triplet = "x86_64-linux-gnu"
        return build_triplet, host_triplet

    def _augment_glib_pkg_config(self):
        """glib 的 proxy-libintl 提供 g_libintl_* 符号，但生成的 glib 系 .pc
        未列 -lintl → 追加（与 libayatana-appindicator-glib / gtk+ 配方一致）。"""
        for pc_name in ("glib-2.0.pc", "gobject-2.0.pc", "gio-2.0.pc"):
            pc_file = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc_file):
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            if "-lintl" in content:
                continue
            if re.search(r"^Libs:", content, flags=re.M):
                content = re.sub(
                    r"^Libs:.*$",
                    lambda m: m.group(0) + " -lintl",
                    content,
                    count=1,
                    flags=re.M,
                )
            else:
                content += 'Libs: -L"${libdir}" -lintl\n'
            with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _provide_missing_glib_pcs(self):
        """把 glib 包内**未被 PkgConfigDeps 生成**的 .pc 补写进 generators 目录。

        机制：PkgConfigDeps 只按依赖包配方 package_info 声明的组件生成 .pc，
        glib 配方未声明 `gio-unix-2.0` 组件 ⇒ 生成目录里没有它；而 libappindicator
        的 configure 明确探测该模块，缺则
        `configure: error: Package requirements (...) were not met:
        No package 'gio-unix-2.0' found`（实测 CI #93264 卡在 build() 里
        `_build_libappindicator()` → `autotools.configure()`；同 SHA 前几次失败
        都在更早的 libdbusmenu configure/make 阶段，所以此前没暴露）。

        事实（本地实测，WSL conan 缓存 glib/2.84.0.1 包内）：包里其实有
        `lib/pkgconfig/gio-unix-2.0.pc`，只是打包成 `prefix=/` 的相对形式，
        直接用会拼出错误的 includedir ⇒ 必须复制到 generators 目录并把 prefix
        改写成包绝对路径（同法见已合入 main 的 appstream/1.2.0、
        aghermann/1.1.2、ayatana-indicator-display/26.6.0）。

        只补 PkgConfigDeps **没生成**的那些文件：已生成的一律不动，避免覆盖
        `_augment_glib_pkg_config` 给 glib-2.0/gobject-2.0/gio-2.0 补的 -lintl。
        """
        glib_package = None
        for dependency in self.dependencies.host.values():
            if dependency.ref.name == "glib" and dependency.package_folder:
                glib_package = dependency.package_folder
                break
        if not glib_package:
            self.output.warning("glib 依赖包目录不可用，跳过 glib 子模块 .pc 补写")
            return
        source_dir = os.path.join(glib_package, "lib", "pkgconfig")
        if not os.path.isdir(source_dir):
            self.output.warning(f"glib 包内无 {source_dir}，跳过 .pc 补写")
            return
        provided = []
        for name in sorted(os.listdir(source_dir)):
            if not name.endswith(".pc"):
                continue
            target = os.path.join(self.generators_folder, name)
            if os.path.exists(target):
                # PkgConfigDeps 已生成（或已补写过）→ 保留原样，不覆盖
                continue
            with open(
                os.path.join(source_dir, name), encoding="utf-8"
            ) as handle:
                content = handle.read()
            # glib 包内 .pc 是 prefix=/ 的打包残留，改写为包绝对路径
            content = re.sub(
                r"^prefix=.*$",
                "prefix=" + glib_package.replace("\\", "/"),
                content,
                count=1,
                flags=re.M,
            )
            with open(target, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            provided.append(name)
        if provided:
            self.output.info(
                "glib 包内 .pc 补写（PkgConfigDeps 未生成，已改写 prefix）: "
                + " ".join(provided)
            )

    def _build_environment(self):
        """构建期环境：私有 prefix + 生成器 .pc 路径、依赖 bin/lib、构建私有
        TMPDIR（HMDFS 上 /tmp 与相对临时目录都不可靠）。"""
        environment = Environment()
        temporary_directory = os.path.join(self.build_folder, "tmp")
        os.makedirs(temporary_directory, exist_ok=True)
        environment.define_path("TMPDIR", temporary_directory)
        environment.define_path("TMP", temporary_directory)
        environment.define_path("TEMP", temporary_directory)
        environment.define_path(
            "PKG_CONFIG_PATH",
            [
                os.path.join(self.generators_folder),
                os.path.join(self._private_prefix, "lib", "pkgconfig"),
            ],
        )
        environment.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self._private_prefix, "lib")
        )
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        environment.prepend_path("PATH", self._tools_shim_dir())
        glib_mkenums = self._glib_mkenums_override()
        if glib_mkenums:
            # AC_ARG_VAR：configure 直接采用，不再走 AC_PATH_PROG
            environment.define("GLIB_MKENUMS", glib_mkenums)
        return environment

    def _glib_mkenums_override(self):
        """返回本次构建应当使用的 `glib-mkenums` 绝对路径（不可用则 None）。

        CI worker 上 PATH 里的 `glib-mkenums` 是 HNP 的 **perl 版**脚本，shebang
        写死 `#!/usr/bin/perl`，而 HarmonyOS PC 的 perl 在
        `/data/service/hnp/bin/perl`（实测 CI #65468/#65495：
        `glib-mkenums: /usr/bin/perl: bad interpreter` → `stamp-enum-types Error
        126`）。本地 WSL 侧依赖包里的同名工具是 python3 版，故本地不复现。

        **关键**：只往 PATH 前面塞 shim 不管用 —— configure 用 AC_PATH_PROG 取
        PATH 中第一个匹配，并把**绝对路径**固化进生成的 Makefile（CI #65495 实证：
        即便 shim 已就位，configure 仍报
        `checking for glib-mkenums... /data/service/hnp/bin/glib-mkenums`）。
        正确做法是用 configure 的 AC_ARG_VAR 接口 `GLIB_MKENUMS=<绝对路径>`
        直接覆盖探测结果（同 xauth 1.1.4 用 XAUTH_CFLAGS/LIBS 绕过 pkg-config 的
        AC_ARG_VAR 逃生口思路）。
        """
        for dependency in self.dependencies.host.values():
            if dependency.ref.name != "glib" or not dependency.package_folder:
                continue
            candidate = os.path.join(
                dependency.package_folder, "bin", "glib-mkenums"
            )
            if not os.path.isfile(candidate):
                continue
            with open(candidate, encoding="utf-8", errors="replace") as handle:
                first_line = handle.readline()
            if first_line.startswith("#!") and "/usr/bin/perl" not in first_line:
                return candidate
            self.output.warning(
                f"glib 包的 glib-mkenums 依赖 /usr/bin/perl，跳过：{first_line.strip()}"
            )
        # 契约：本函数只返回「可直接执行的 glib-mkenums 脚本绝对路径」，否则 None。
        # 这里**不能**把 perl 解释器路径当作 glib-mkenums 返回：调用方（GLIB_MKENUMS
        # 环境变量）会把该值冻结进 Makefile，make 随后执行 `perl --template ...`
        # （缺脚本首参）直接报 "Unrecognized switch" —— 必然失败，不是降级。
        # 经 perl 转发的降级由 _tools_shim_dir() 的包装脚本负责（它会带上脚本首参）。
        self.output.warning(
            "glib 包未提供可直接执行的 glib-mkenums（其 shebang 依赖 /usr/bin/perl）"
        )
        return None

    def _tools_shim_dir(self):
        """构建期工具 shim 目录（只放本配方自己造的包装脚本）。

        `glib-mkenums` 本身靠 `GLIB_MKENUMS` 环境变量覆盖（见
        `_glib_mkenums_override`，PATH 前置不可靠）；这里额外放一个同名包装，
        用于**没有** AC_ARG_VAR 逃生口的调用方（例如直接 `find_program()` 的
        下游构建系统）。包装优先 exec 依赖包内可用实现，否则经 OHOS 的 perl
        转发。
        """
        shim_dir = os.path.join(self.build_folder, "tools-shim")
        os.makedirs(shim_dir, exist_ok=True)
        target = os.path.join(shim_dir, "glib-mkenums")
        candidate = self._glib_mkenums_override()
        if candidate:
            body = f'#!/bin/sh\nexec "{candidate}" "$@"\n'
            self.output.info(f"glib-mkenums shim -> {candidate}")
        else:
            # 依赖包内没有可直接执行的 glib-mkenums：退化为经 OHOS 的 perl 转发。
            # glib-mkenums 本身是一个 perl 脚本，调用方（configure/automake）传进来的
            # "$@" 已经包含脚本路径，所以这里只需 exec perl，**不要**再补首参。
            perl = "/data/service/hnp/bin/perl"
            body = (
                "#!/bin/sh\n"
                f'if [ -x "{perl}" ]; then exec "{perl}" "$@"; fi\n'
                'echo "glib-mkenums shim: no usable implementation on this host" >&2\n'
                "exit 127\n"
            )
            self.output.warning(
                "glib 依赖未提供可用的 glib-mkenums；shim 退化为 "
                f"{perl} 转发（本机可能不存在，仅 OHOS 上有）"
            )
        with open(target, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
        os.chmod(target, 0o755)
        return shim_dir

    # ------------------------------------------------------------------- build
    def build(self):
        apply_conandata_patches(self)
        mkdir(self, self._private_prefix)
        self._relocate_dep_la_files()
        # 构建期环境（PKG_CONFIG_PATH / LD_LIBRARY_PATH / TMPDIR 等）用
        # Environment.apply() 注入当前进程，子进程与 Autotools helper 均继承
        # （libayatana-appindicator-glib 2.0.3 先例同法）。
        with self._build_environment().vars(self).apply():
            self._build_libdbusmenu()
            self._build_libappindicator()

    def _relocate_dep_la_files(self):
        """依赖包里的 libtool 归档记录了发布构建机的前缀（实测 libdir='/'
        或旧 conan 缓存路径），本机 libtool 读到后会拼出 `//lib/libfreetype.la`
        这类不可解析路径并以

            libtool: error: '//lib/libfreetype.la' is not a valid libtool archive

        中断链接（同时伴随大量 "library ... was moved" 警告）。就地改写为当前
        实际目录并清空 dependency_libs（共享库链接不需要 .la 里的传递依赖，
        gtk+-3.0.pc 已给出完整链接行；同 xauth 1.1.4 / libxp 1.0.4 做法）。
        """
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if not os.path.isdir(libdir):
                    continue
                for entry in sorted(os.listdir(libdir)):
                    if not entry.endswith(".la"):
                        continue
                    path = os.path.join(libdir, entry)
                    with open(path, encoding="utf-8", errors="replace") as handle:
                        content = handle.read()
                    fixed = re.sub(
                        r"^libdir=.*$", f"libdir='{libdir}'", content, flags=re.M
                    )
                    fixed = re.sub(
                        r"^dependency_libs=.*$",
                        "dependency_libs=''",
                        fixed,
                        flags=re.M,
                    )
                    if fixed != content:
                        with open(path, "w", encoding="utf-8") as handle:
                            handle.write(fixed)
                        self.output.info(f"依赖 .la 已重定位: {entry} -> {libdir}")

    def _build_libdbusmenu(self):
        """随包构建 libdbusmenu 16.04.0 → 私有 prefix（R49）。"""
        src = os.path.join(self.source_folder, "libdbusmenu-src")
        build_dir = os.path.join(self.build_folder, "libdbusmenu-build")
        mkdir(self, build_dir)
        configure = os.path.join(src, "configure")
        # ★关键★ --build 与 --host **必须不同**，否则整套三元组注入反而制造出
        # CI #90732 的静默 rc=1（本地已逐行复现，见下方注释）。
        build_triplet, host_triplet = self._libdbusmenu_triplets()
        args = [
            f"--prefix={self._private_prefix}",
            "--with-gtk=3",
            # 老版 config.guess 不认 HarmonyOS（CI worker 原生构建时 configure 会
            # 直接失败），显式给出 GNU 三元组绕开探测（见 _gnu_triplet 说明）。
            f"--build={build_triplet}",
            f"--host={host_triplet}",
            "--disable-static",
            "--disable-nls",      # 不交付 NLS 消息目录（也避免依赖 gettext 工具）
            "--disable-dumper",   # dumper 需要 gtk+-2.0（不在依赖链内）
            "--disable-tests",    # 上游 tests 需要 json-glib（不在依赖链内）
            "--disable-vala",     # OHOS 无 vapigen
        ]
        # HMDFS（E114/E236）：autoconf 生成的 configure/config.status 里有**写死
        # 的子 shell** `(umask 077 && mktemp -d "./confXXXXXX")`（回退分支是
        # `(umask 077 && mkdir "$tmp")`），在其中写 subs1.awk 后**再次读取**；
        # OHOS 文件系统（HMFS/HMDFS）拒绝这套“私有临时目录 + 二次读取”的权限模型。
        # 实测 CI（#65144 / #65460，两次都在同一行）：
        #     ./config.status: line 836: ./confXXXXXX/subs1.awk: Permission denied
        #     config.status: error: could not setup config files machinery
        # 本地实证（同一 autoconf 版本，唯一变量是该行的 umask）：
        #     写死 umask 077 → 目录 drwx------ (0700)、文件 -rw------- (0600)
        #     改写为 umask 022 → 目录 drwxr-xr-x (0755)、文件 -rw-r--r--
        # 注意：**在外层 shell 里 `umask 000 && configure` 无效**（已实测）：那两处
        # umask 在脚本自己的子 shell 里，外层 umask 影响不到；必须改写脚本文本。
        # 且 configure 会把这两行**原样复制**进它生成的 config.status（本地比对
        # configure:2453/2458 ↔ config.status:546/551），故改写 configure 即同时
        # 修好两处执行阶段。只改随包依赖的预生成脚本，不触碰 libappindicator
        # 上游、不触碰任何测试用例源码。
        for old, new in (
            ("(umask 077 && mktemp -d", "(umask 022 && mktemp -d"),
            ('(umask 077 && mkdir "$tmp")', '(umask 022 && mkdir "$tmp")'),
        ):
            replace_in_file(self, configure, old, new, strict=False)
        with open(configure, encoding="utf-8") as handle:
            if "umask 077" in handle.read():
                raise ConanException(
                    "随包 libdbusmenu 的 configure 仍含 umask 077（HMDFS 上会导致 "
                    f"config.status: could not setup config files machinery）：{configure}"
                )
        self.output.info(
            "libdbusmenu configure: tmp-dir umask 022 (E114 HMDFS pattern)"
        )
        # 注意：该 `(set -o)` 探测在随包 configure 里出现 **3 次**，必须区分：
        #   行 29   —— 头部探测，**可执行**，会 fork（本次要修的第一个点）
        #   行 173  —— 转义后位于引号 heredoc 内的**说明文本**，不会执行，保持原样
        #   行 16342—— `config.status` 机制段，**可执行**，同样会 fork
        #             （与上面 umask 注释同理：configure 会把这段原样复制进它生成的
        #              config.status，所以两处都要改，否则 config.status 阶段仍 fork）
        # 故这里对**两个可执行点**各替换一次，并对转义文本不做任何改动。
        _posix_probe_old = (
            "  case `(set -o) 2>/dev/null` in #(\n"
            "  *posix*) :\n"
            "    set -o posix ;; #(\n"
            "  *) :\n"
            "     ;;\n"
            "esac\n"
        )
        # 替换必须同时满足三条（本地逐条实测，见 notes.md）：
        #   ① 不 fork —— 原来那次 fork 就出在反引号命令替换上；
        #   ② dash 上不能致命 —— 实测 dash 执行 `set -o posix` 会**立即以 2 退出**
        #      （`set: Illegal option -o posix`），`|| :` 兜不住，整个 configure 会
        #      在头部静默死掉（rc=2、零输出）；
        #   ③ 语义不变 —— 原语义是“支持 POSIX 模式就开启它”。
        # 故用 fork-free 的特性判断（`${BASH_VERSION+set}`，纯变量展开）把
        # `set -o posix` 只放在确实支持它的 shell 上执行；dash 走空分支，
        # 与原写法在 dash 上“匹配不到 *posix*、分支体从不执行”净效果一致。
        # 实测：dash/bach 均 rc=0，头部 fork 数 0。
        _posix_probe_new = (
            "  # fork-free POSIX-mode probe (see conanfile comment): the original\n"
            "  # backtick `(set -o)` command substitution forks, which fails on a\n"
            "  # worker under fork pressure (CI: configure[35]: can't fork).\n"
            "  # `set -o posix` is fatal on dash, so gate it on real support.\n"
            "  if test -n \"${BASH_VERSION+set}\"; then\n"
            "    set -o posix\n"
            "  fi\n"
        )
        with open(configure, encoding="utf-8") as handle:
            _cfg = handle.read()
        # 逐个替换所有**未转义**的可执行探测点（实测 2 处：头部 + config.status
        # 机制段）。注意 conan 的 replace_in_file 一次会替换**全部**匹配，所以
        # 用“替换前后剩余匹配数之差”来统计真正改了几处，而不是数循环次数
        # （早期版本数循环次数，2 处只记成 1，日志与事实不符）。
        # 转义文本（行 173）不含未转义反引号，不会被匹配到。
        _probe = "case `(set -o) 2>/dev/null` in"
        _before = _cfg.count(_probe)
        if _before == 0:
            raise ConanException(
                "随包 libdbusmenu 的 configure 未找到 fork 版 POSIX 探测"
                f"（上游快照或补丁顺序可能已变化）：{configure}"
            )
        replace_in_file(
            self, configure, _posix_probe_old, _posix_probe_new, strict=False
        )
        with open(configure, encoding="utf-8") as handle:
            _cfg = handle.read()
        _after = _cfg.count(_probe)
        _fixed = _before - _after
        if _after != 0 or _fixed == 0:
            raise ConanException(
                "随包 libdbusmenu 的 configure 仍含 fork 版 POSIX 探测"
                f"（替换前 {_before} 处、后 {_after} 处；worker fork 紧张时会 "
                f"configure[35]: can't fork）：{configure}"
            )
        self.output.info(
            f"libdbusmenu configure: POSIX probe made fork-free in {_fixed} site(s) "
            "(CI can't-fork hardening)"
        )
        # glib-mkenums：configure 用 AC_PATH_PROG 取 **PATH 中第一个**匹配，并把
        # 绝对路径写死进生成的 Makefile（实测 CI #65495：`checking for
        # glib-mkenums... /data/service/hnp/bin/glib-mkenums`，随后 make 报
        # `/usr/bin/perl: bad interpreter`）。因此：
        #   ① PATH 里放 shim 不够 —— HNP 的 bin 仍可能先命中，且路径会被固化；
        #   ② GLIB_MKENUMS 是 AC_ARG_VAR（configure:726 的 AC_ARG_VAR 列表里），
        #      环境变量可直接覆盖探测结果，是唯一稳的注入点。
        glib_mkenums = self._glib_mkenums_override()
        if glib_mkenums:
            self.output.info(f"GLIB_MKENUMS override -> {glib_mkenums}")
        # 整条命令行统一用 shlex.join 转义：args 里含 `--prefix=<build_folder>`
        # 等内嵌路径，只对 configure 单独 quote 会让含空格/元字符的路径破坏命令
        # （与 package() 里对 patchelf 目标的处理保持一致）。
        # ★fail-closed 守卫（本轮新增）★
        # 补丁 0004 把随包 libdbusmenu 的 intltool 版本**取值**改为常量
        # （INTLTOOL_APPLIED_VERSION_AS_INT=51000），使其恒 >= 要求的 3500。
        # 注意：补丁**没有**删除后面那句
        #     as_fn_error $? "Your intltool is too old. ..."
        # （它在 hunk 之外，仍留在文件里）——保住它是对的，因为断言本身
        # `test $APPLIED -ge 3500` 依然起作用，只是左侧恒为 51000。
        #
        # 若该补丁因任何原因**未生效**，configure 会在
        #   checking for intltool >= 0.35.0... found
        # 之后**静默退出**（rc=1、stdout 到此为止、stderr 为空）：OHOS 镜像没有
        # intltool-update，APPLIED 取空 -> 0 >= 3500 为假 -> 触发 as_fn_error，
        # 而 dash 下该错误路径不产生可观测量。实测复现与 CI #89171 症状逐字一致。
        #
        # conanfile 原先只自检 umask 与 POSIX fork 探测两处，缺这一条，
        # 于是"补丁没打到"会表现为一个没有任何线索的失败。这里补上自检。
        with open(configure, encoding="utf-8") as handle:
            _cfg_guard = handle.read()
        if "INTLTOOL_APPLIED_VERSION_AS_INT=51000" not in _cfg_guard:
            raise ConanException(
                "随包 libdbusmenu 的 configure 未见 0004 补丁的 intltool 版本改写"
                "（期望 INTLTOOL_APPLIED_VERSION_AS_INT=51000；若缺失，OHOS 镜像"
                "无 intltool-update，configure 会在 intltool 探测处静默 rc=1 且"
                f"无任何 stderr）：{configure}"
            )
        if "intltool-update --version" in _cfg_guard:
            raise ConanException(
                "随包 libdbusmenu 的 configure 仍在**运行期**调用 intltool-update "
                "取版本（0004 未完全生效；OHOS 镜像无该工具，会导致 intltool 断言"
                f"失败）：{configure}"
            )
        self.output.info("libdbusmenu configure: intltool probe relaxed (0004 verified)")

        self.run(
            shlex.join([configure, *args]),
            cwd=build_dir,
            env="conanbuild",
        )
        self.run("make", cwd=build_dir, env="conanbuild")
        # 上游 libdbusmenu-gtk/Makefile.am 把 dbusmenu-gtk.h 等同时列进
        # libdbusmenu_gtkinclude_HEADERS 与 libdbusmenu_gtk3include_HEADERS，
        # 并行 make install 时两条规则并发安装同一个头文件 → 实测
        # "/usr/bin/install: cannot create regular file ...: File exists" →
        # install-libdbusmenu_gtk3includeHEADERS Error 1（与 package() 里外层
        # make install -j1 同因）。这是竞态：同一提交多次跑会时好时坏
        # （本地实测先 3 次通过、随后 2 次连续失败），串行安装即可根治。
        self.run("make install -j1", cwd=build_dir, env="conanbuild")
        self.output.info(
            "private prefix after libdbusmenu install: "
            f"{sorted(os.path.relpath(p, self._private_prefix) for p in glob.glob(os.path.join(self._private_prefix, '**', '*'), recursive=True))[:40]}"
        )

    def _build_libappindicator(self):
        # autoreconf 的 config.guess/config.sub 来自构建机 automake，内容随
        # 构建机变化，故按 E007 在生成后补 linux-ohos 支持（见模块 docstring）。
        self.run(
            "autoreconf -fi -I m4", cwd=self.source_folder, env="conanbuild"
        )
        self._fix_generated_autotools_files()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # 编译上游可编译的测试程序（API 消费面证据）：
        #   test-libappindicator（9 个 g_test 用例，test_package 中真实执行）
        #   test-simple-app（最小消费者示例）
        # 其余 6 个程序需要 dbus-glib-1（TESTDEPS），见 requirements() 说明与
        # MANIFEST.yml；上游 make check 的 4 个 TESTS 脚本需要 Xvfb +
        # dbus-test-runner，OHOS 平台不可运行，故不执行（同样见 MANIFEST.yml）。
        self.run(
            "make -C tests test-libappindicator test-simple-app",
            cwd=self.build_folder,
            env="conanbuild",
        )

    def _fix_generated_autotools_files(self):
        # autoreconf 把**构建机 automake 自带**的 config.sub 复制进 src/，其
        # 结构随版本变（CI #92718 实测）：
        #   * 系统 automake 1.16（本地 WSL）→ 2022-01-03 版：基本系统类型是
        #     **单行** `gnu* | android* | bsd* | mach* …`，且**不认 ohos**；
        #   * conan automake/1.18（CI worker）→ 2024-05-27 版：白名单改为
        #     每行一项的 `| gnu* \ …` 列表（旧单行 pattern 已不存在，严格
        #     replace_in_file 直接抛“didn't find pattern”——CI #92718 首错），
        #     且上游**已内置** `| ohos*` 与 `linux-ohos*-`，根本无需注入。
        # 故按结构分支注入，最后用**真执行 config.sub** 做 fail-closed 行为
        # 校验（比子串比对强：注入没生效也能抓住）。
        config_sub = os.path.join(self.source_folder, "config.sub")
        with open(config_sub, encoding="utf-8") as handle:
            content = handle.read()
        if "gnu* | android* | bsd*" in content:
            # (a) 基本系统类型白名单（E007，老版单行结构）
            replace_in_file(
                self,
                config_sub,
                "gnu* | android* | bsd*",
                "gnu* | android* | ohos* | bsd*",
                strict=True,
            )
            # (b) 2022+ 版 config.sub 另有一张 kernel-os 配对白名单，只补 (a) 仍会
            #     报 "Invalid configuration `aarch64-linux-ohos': Kernel `linux' not
            #     known to work with OS `ohos'"
            replace_in_file(
                self,
                config_sub,
                "\t*-eabi* | *-gnueabi*)\n\t\t;;\n",
                "\t*-eabi* | *-gnueabi*)\n\t\t;;\n\tlinux-ohos*)\n\t\t;;\n",
                strict=False,
            )
            self.output.info(
                "config.sub: ohos injected into legacy (<=2022) whitelists (E007)"
            )
        elif "ohos*" in content and "linux-ohos*" in content:
            # 2024-05-27 起上游 config.sub 已内置 ohos（CI automake/1.18 所带
            # 版本实测：`sh config.sub aarch64-linux-ohos` → rc=0）。
            self.output.info(
                "config.sub: ohos supported natively (2024-05-27+), no injection"
            )
        else:
            raise ConanException(
                "config.sub 结构无法识别：既无老版单行白名单可注入，也不含 ohos "
                f"支持（构建机 automake 版本未知？）：{config_sub}"
            )
        # fail-closed 行为校验（E007）：真执行 config.sub 问它认不认目标三元组
        # （subprocess 直调、捕获双流——不依赖 self.run 的 shell 语义）。
        check_triple = re.sub(r"gnu$", "ohos", self._gnu_triplet(self.settings))
        proc = subprocess.run(
            ["/bin/sh", config_sub, check_triple],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        got = proc.stdout.strip()
        combined = got + "\n" + proc.stderr
        if proc.returncode != 0 or "Invalid" in combined:
            raise ConanException(
                f"config.sub 拒绝 {check_triple}（E007 注入未生效？）"
                f" rc={proc.returncode}：{(proc.stderr or got).strip()[:300]}"
                f"（{config_sub}）"
            )
        if not got.startswith(check_triple.split("-")[0]) or "linux-ohos" not in got:
            raise ConanException(
                f"config.sub 对 {check_triple} 输出异常（E007）：{got!r}"
            )
        self.output.info(
            f"config.sub: {check_triple} accepted (E007 behavior check) -> {got}"
        )
        configure = os.path.join(self.source_folder, "configure")
        for old, new in (
            ("(umask 077 && mktemp -d", "(umask 022 && mktemp -d"),
            ('(umask 077 && mkdir "$tmp")', '(umask 022 && mkdir "$tmp")'),
        ):
            replace_in_file(self, configure, old, new, strict=False)
        self.output.info("configure: tmp-dir umask 022 (E114 HMDFS pattern)")

    # ----------------------------------------------------------------- package
    def package(self):
        autotools = Autotools(self)
        # 上游 src/Makefile.am 把 app-indicator-enum-types.h 同时列进
        # libappindicatorinclude_HEADERS 与 nodist_libappindicatorinclude_HEADERS，
        # 并行 `make install` 时两条规则装同一个目标文件 → 实测
        # `install: cannot create regular file ...: File exists`；
        # 串行安装即可（-j1，与 .la 链接阶段同因）。
        autotools.install(args=["-j1"])
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING*",
            src=os.path.join(self.source_folder, "libdbusmenu-src"),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # 随包交付的 libdbusmenu（私有 prefix → 包内 lib/include/pkgconfig）
        copy(
            self,
            "libdbusmenu-*.so*",
            src=os.path.join(self._private_prefix, "lib"),
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )

        # 静态链接配置下（实测 -c tools.build:exelinkflags=['-static']，本地
        # profile ohos-aarch64-local 就带这一条）libtool 产出的是 .a 归档而不是
        # .so；只拷 .so* 会让包内丢掉 libdbusmenu-glib/gtk3，而 package_info()
        # 仍然声明这两个库 → 消费方 CMakeDeps 直接报
        # "Library 'dbusmenu-gtk3' not found in package"。
        # 存在 .a 时一并交付，两种配置下包内容都与 cpp_info.libs 自洽。
        if glob.glob(os.path.join(self._private_prefix, "lib", "libdbusmenu-*.a")):
            copy(
                self,
                "libdbusmenu-*.a",
                src=os.path.join(self._private_prefix, "lib"),
                dst=os.path.join(self.package_folder, "lib"),
                keep_path=False,
            )
        copy(
            self,
            "*.pc",
            src=os.path.join(self._private_prefix, "lib", "pkgconfig"),
            dst=os.path.join(self.package_folder, "lib", "pkgconfig"),
            keep_path=False,
        )
        # 随包 dbusmenu 头文件保留上游布局
        # include/libdbusmenu-glib-0.4/libdbusmenu-glib/*.h（.pc 的 Cflags 指向
        # include/libdbusmenu-glib-0.4，故必须整棵子树复制，不能只取顶层 *.h）。
        for inc_dir in glob.glob(
            os.path.join(self._private_prefix, "include", "libdbusmenu*")
        ):
            shutil.copytree(
                inc_dir,
                os.path.join(
                    self.package_folder, "include", os.path.basename(inc_dir)
                ),
                dirs_exist_ok=True,
            )
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share", "gtk-doc"))
        self._relocate_pkg_config_prefixes()
        # 顺序固定：先去 DT_RUNPATH，再签名（签名是内容哈希，改字节即失效）。
        self._strip_build_machine_rpath()
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def _strip_build_machine_rpath(self):
        """libtool 会把安装前缀（conan 缓存的私有 prefix）与依赖 libdir 写进
        DT_RUNPATH，随包发布就是构建机死路径（实测 libappindicator3.so.1.0.0
        的 RUNPATH 含 /root/.conan2/p/... 与私有 prefix；同族既有制品
        gtk/3.24.43、glib/2.84.0.1 均无 RUNPATH，xcfa 消费方用例把
        "无 RPATH/RUNPATH" 列为自检项）。发布前用 patchelf 去掉；运行期寻库
        由消费方 Conan 的 LD_LIBRARY_PATH / RPATH 负责。
        """
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ):
            targets.extend(glob.glob(pattern, recursive=True))
        targets = [
            target
            for target in sorted(set(targets))
            if not os.path.islink(target) and os.path.isfile(target)
        ]
        if not targets:
            return
        patchelf = shutil.which("patchelf")
        if not patchelf:
            self.output.warning(
                "patchelf not available — build-machine DT_RUNPATH left in place"
            )
            return
        for target in targets:
            # 统一用 shlex.join：package_folder 路径可能含空格或 shell 元字符，
            # 仅加双引号既不能防注入也会在含 `"` 的路径上破坏命令。
            self.run(shlex.join([patchelf, "--remove-rpath", target]))
        self.output.info(f"DT_RUNPATH removed from {len(targets)} shared objects")

    def _relocate_pkg_config_prefixes(self):
        """包内 .pc 的 prefix 必须可重定位：上游 appindicator3-0.1.pc 与随包
        libdbusmenu 的 .pc 都记录了安装时的前缀（conan 缓存/构建私有目录），
        拷进包后在别的机器上就是死路径。统一改写为 ${pcfiledir}/../..（.pc 位
        于 <pkg>/lib/pkgconfig，回到包根）。"""
        pkgconfig = os.path.join(self.package_folder, "lib", "pkgconfig")
        for entry in sorted(glob.glob(os.path.join(pkgconfig, "*.pc"))):
            with open(entry, encoding="utf-8") as handle:
                content = handle.read()
            fixed = re.sub(
                r"^prefix=.*$", "prefix=${pcfiledir}/../..", content, flags=re.M
            )
            if fixed != content:
                with open(entry, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(fixed)
                self.output.info(f".pc prefix 已重定位: {os.path.basename(entry)}")

    def _sign_installed_elfs(self):
        """OHOS 上 .so 需去 .codesign 段并自签名后才能被执行器加载。
        交叉构建机（本地 qemu 验证）无签名工具 —— 与 xdp-tools 等配方一致：
        警告并跳过（qemu 不校验 codesign），CI/真机构建时工具存在则真实签名。"""
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            self.output.warning(
                "OHOS signing tools not found (cross build host) — skip signing; "
                "qemu validation does not enforce codesign, CI/device signs"
            )
            return
        targets = []
        for pattern in (
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ):
            targets.extend(glob.glob(pattern, recursive=True))
        for target in sorted(set(targets)):
            if os.path.islink(target) or os.path.isdir(target):
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{target}"')
            self.run(
                f'"{signer}" sign -inFile "{target}" -outFile "{target}" -selfSign 1'
            )

    def package_info(self):
        # 上游 src/appindicator3-0.1.pc：Libs -lappindicator3，
        # Requires: dbusmenu-glib-0.4 gtk+-3.0（随包交付 dbusmenu 运行库）。
        self.cpp_info.libs = ["appindicator3", "dbusmenu-gtk3", "dbusmenu-glib"]
        # 头闭包：上游 .pc 的 Cflags 是 -I${includedir}/libappindicator3-0.1，
        # 随包 dbusmenu 头在 include/libdbusmenu-{glib,gtk3}-0.4（各自 .pc 同款），
        # 因此三处都要作为 include 目录暴露，消费方才能
        # #include <libappindicator/app-indicator.h> 与 <libdbusmenu-glib/*.h>。
        self.cpp_info.includedirs = [
            "include",
            "include/libappindicator3-0.1",
            # 上游自己的 tests/ 与 example/ 用裸名 `#include <app-indicator.h>`
            # （树内 -I$(top_srcdir)/src）；一并暴露，保证两种包含写法都能编译。
            "include/libappindicator3-0.1/libappindicator",
            "include/libdbusmenu-glib-0.4",
            "include/libdbusmenu-gtk3-0.4",
        ]
        self.cpp_info.set_property("pkg_config_name", "appindicator3-0.1")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
