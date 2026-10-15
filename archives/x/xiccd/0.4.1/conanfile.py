#!/usr/bin/env python3
"""Conan recipe — xiccd 0.4.1（X11 色彩配置守护进程）

Build system: autotools（configure.ac + Makefile.am，根 Makefile.am 直接编译 src/*.c）
License: GPL-3.0-or-later
Homepage: https://github.com/agalakhov/xiccd

功能：监听 RandR 输出的连接/断开，把对应的 ICC 色彩配置推送给 colord（X 色彩管理）。

OHOS 适配点：
  - GitHub tag archive 不含预生成 configure（autoreconf 产物不进版本库），build() 先
    autoreconf -fi 自举。真机自带 automake 1.19 损坏：am/ 数据文件里 `@datadir@`
    占位符未展开（autoreconf 报 "cannot open < @datadir@/automake-1.19/am/header-vars.am"
    且 "./compile not found"）→ 经 tool_requires automake/1.18 + libtool/2.5.4 用
    build profile 解析（E178，同 xsel/1.2.1、afuse、argp-standalone）。
  - configure.ac 四个硬性 PKG_CHECK_MODULES：x11 / xrandr>=1.3 / glib-2.0>=2.36 /
    colord>=1.0.2，全部由 conan 依赖提供（libx11 / libxrandr / glib2 / colord）；
    PkgConfigDeps 把 .pc 生成到 generators 目录，build() 内作用域注入 PKG_CONFIG_PATH
    （真机实测 tc.environment()/PkgConfigDeps 自动注入不生效，xsel、pidgin 同款坑）。
  - 真机 pkg-config 0.29.2 的 pkg.m4 供 aclocal 使用（PKG_CHECK_MODULES 宏来源）。
  - E444（GObject 多副本）：ohpcd 只发静态 glib2，直接链进 exe 会与 colord 的
    libcolordprivate.so.2 内嵌 glib 构成两份 GObject 类型系统 → 加载期 abort。修法见
    generate() 的 _unify_glib_single_copy()（去源头：glib 系 .pc Libs 置空，g_* 统一
    解析到 libcolordprivate.so.2 导出的唯一副本；先例 gssdp/1.6.6、gupnp/1.6.8）。
  - E114：autoreconf 生成的 configure 用 umask 077 建临时目录，HMDFS 下不可写 → 改 022。
  - HMFS/HMDFS 不支持 getcwd：进程 cwd 切到 build_folder 并预置 PWD，同时改写 configure
    的 ac_pwd/pwd 判定（同 xsel/1.2.1、aribb24/1.0.4）。
  - 补丁 0001 固化 AC_INIT 版本：上游写的是 m4_esyscmd_s([git describe ...])，tarball
    无 .git → 展开为空串，二进制 `-V` 不带版本号（powerman/2.4.4、cowdancer/0.90 同型）。
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XiccdConan(ConanFile):
    name = "xiccd"
    version = "0.4.1"
    description = "X color profile daemon — 监听 RandR 输出变化并把 ICC 色彩配置推送给 colord"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/agalakhov/xiccd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # X11 栈统一走 cmd-pkgs 6.4.0 线（libx11/6.4.0 + libxext/6.4.0）：libxrandr/1.5.5.1
        # 以 force=True 钉 libx11/6.4.0，其已发布的 OHOS armv8 binary 可直接复用；
        # 旧的 1.8.13 线会让 libX11.la 引用 libxcb.la（libxcb 不发布 .la），
        # 任何下游源码构建都撞 libtool "not a valid libtool archive"。
        self.requires("libx11/6.4.0", headers=True, libs=True)
        self.requires("libxrandr/1.5.5.1", headers=True, libs=True)
        # glib2 必须与 colord/1.4.8.1 声明的一致（2.88.0），否则版本冲突并触发
        # colord/glib2 源码重编译。
        self.requires("glib2/2.88.0", headers=True, libs=True)
        self.requires("colord/1.4.8.1", headers=True, libs=True)

    def build_requirements(self):
        # tag archive 无 configure（须 autoreconf）+ 真机 automake 损坏 → E178
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps 为每个依赖生成 .pc（x11 / xrandr / glib-2.0 / colord 及其
        # Requires 链），configure 的四个 PKG_CHECK_MODULES 全靠它们解析。
        PkgConfigDeps(self).generate()
        AutotoolsToolchain(self).generate()
        self._unify_glib_single_copy()

    def _unify_glib_single_copy(self):
        """E444／GObject 单副本：让 bin/xiccd 的 glib 符号全部来自 colord 导出的副本。

        ohpcd 只发布静态 glib2（libglib-2.0.a/libgobject-2.0.a…，无 .so）。PkgConfigDeps
        在 generators/ 下生成的 glib-2.0.pc 其 Libs 带全量静态 glib 链接列表，于是
        Makefile.am 的 $(GLIB_LIBS) 会把 libglib-2.0.a 等链进 bin/xiccd。而
        colord/1.4.8.1 的 libcolordprivate.so.2 同样内嵌了一份 glib 并导出全部
        g_*/g_object_*/g_io_* 符号（nm -D 实测 4123 个）—— 进程内于是有两份 GObject
        类型系统。libtool 默认给程序加 -export-dynamic，使 exe 里那份静态 glib 也参与
        全局符号插入；而 ELF 初始化顺序是「先依赖库构造器、后 exe 构造器」，于是
        libcolordprivate 的构造器调到的是 exe 里尚未初始化的 glib，加载期直接 abort：

            GLib-GObject:ERROR:../gobject/gtype.c:2555:g_type_register_static:
            assertion failed: (static_quark_type_flags)      → Signal 6

        （本地最小复现：`静态 glib + -lcolord` 的空 main 即崩，rc=134；只静态链 glib
        或只链 colord 均正常，故根因是「exe 内再嵌一份 glib」而非某一方的缺陷。）

        修法沿用同栈先例 gssdp/1.6.6 · gupnp/1.6.8 的「去源头」方案：把 glib 系 .pc 的
        Libs 置空，静态 glib 完全不进入链接；exe 对 g_* 的引用全部变成 UND，运行时统一
        解析到 colord.pc 已声明的 libcolordprivate.so.2 所导出的唯一 gobject 副本 ——
        全进程单 GObject 域（实测 g_object_new/GMainLoop 均正常，R40 级平台适配）。
        注意 gssdp 已证伪的对照修法：`-Wl,--exclude-libs,ALL` 只隐藏动态符号表，.so
        内部对静态库符号的引用在链接期已绑定到未初始化的本地副本 → 仍然崩。

        Cflags 必须保留（src/*.c 需要 <glib.h>/<gio/gio.h> 头文件）；Requires 链上的
        pcre2/zlib 静态归档未被引用，不会被拉进 exe（与 gssdp/1.6.6 一致）。
        """
        gen_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(gen_pc):
            return
        with open(gen_pc, "r", encoding="utf-8") as f:
            text = f.read()
        # 只清空 Libs 行（保留 Cflags/Version/Requires，PKG_CHECK_MODULES 版本检查不受影响）
        for prefix in ("Libs:", r"Libs\.private:"):
            text = re.sub(rf"^{prefix}.*$", prefix.replace("\\", ""), text, flags=re.M)
        with open(gen_pc, "w", encoding="utf-8") as f:
            f.write(text)

    def build(self):
        # HMFS/HMDFS 不支持 getcwd：把进程 cwd 切到 build_folder（路径查找可用、
        # 仅 getcwd 不可用），并预置 PWD 让子 shell 的 pwd 内建走逻辑路径。
        try:
            os.chdir(self.build_folder)
        except OSError:
            pass
        os.environ["PWD"] = self.build_folder

        os.umask(0)
        apply_conandata_patches(self)
        self._prepare_aclocal_path()
        # tag archive 无 configure，先自举（automake/libtool 来自 tool_requires）
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        self._patch_configure()
        autotools = Autotools(self)
        # 真机 conan 的 tc.environment()/PkgConfigDeps 注入 PKG_CONFIG_PATH 实测不生效，
        # 改为 build() 内作用域注入：generators 目录（PkgConfigDeps 产物）+ 各依赖
        # 包 lib/pkgconfig；try/finally 保证返回前恢复。
        _pc_paths = [self.generators_folder]
        for _dep in self.dependencies.values():
            _pc_paths.append(os.path.join(_dep.package_folder, "lib", "pkgconfig"))
        _pkg_config_path = ":".join(_pc_paths)
        _prior_pkg_config_path = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = _pkg_config_path
        self.output.info(f"PKG_CONFIG_PATH (scoped) = {_pkg_config_path}")
        try:
            autotools.configure()
            autotools.make(args=["-j1"])
        finally:
            if _prior_pkg_config_path:
                os.environ["PKG_CONFIG_PATH"] = _prior_pkg_config_path
            else:
                os.environ.pop("PKG_CONFIG_PATH", None)

    def _patch_configure(self):
        """autoreconf 后改写生成的 configure：
        - E114: config.status 用 umask 077 建临时目录，HMDFS 下不可写 → 改 022；
        - HMFS 下 getcwd 不可达致 configure 报 'working directory cannot be
          determined'：按 autoconf 版本改写 pwd 判定（同 xsel/1.2.1、aribb24/1.0.4）。
        """
        cfg = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(cfg):
            return
        with open(cfg, "r", encoding="utf-8") as f:
            text = f.read()
        if "umask 077" in text:
            text = text.replace("umask 077", "umask 022")
        if 'ac_pwd=`pwd`' in text and 'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"' not in text:
            text = text.replace('ac_pwd=`pwd`', 'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"')
        text = re.sub(
            r'if \(pwd\) >/dev/null 2>&1( && test -d "`pwd`")?; then :; else',
            r'if (pwd) >/dev/null 2>&1\1 || test -n "$PWD"; then :; else',
            text,
        )
        with open(cfg, "w", encoding="utf-8") as f:
            f.write(text)

    def _prepare_aclocal_path(self):
        """pkg.m4（PKG_CHECK_MODULES 宏）供 aclocal 使用：动态定位 pkg-config 安装目录
        （aircrack-ng 同法），并兜底扫描 hnp 工具链 aclocal 目录（afuse 同法）。"""
        dirs = []
        pkg_config = shutil.which("pkg-config")
        if pkg_config:
            prefix = os.path.dirname(os.path.dirname(os.path.realpath(pkg_config)))
            cand = os.path.join(prefix, "share", "aclocal")
            if os.path.isfile(os.path.join(cand, "pkg.m4")):
                dirs.append(cand)
        for d in sorted(glob.glob("/data/service/hnp/*/*/share/aclocal")):
            if os.path.isfile(os.path.join(d, "pkg.m4")):
                dirs.append(d)
        if dirs:
            existing = os.environ.get("ACLOCAL_PATH", "")
            os.environ["ACLOCAL_PATH"] = ":".join(dirs + ([existing] if existing else []))

    def package(self):
        Autotools(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # 命令行守护进程：产物 bin/xiccd + man8，无可链接库
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
