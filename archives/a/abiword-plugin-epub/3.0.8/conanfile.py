#!/usr/bin/env python3
"""Conan recipe — abiword-plugin-epub 3.0.8

AbiWord EPUB e-book export plugin.
Part of the AbiWord 3.0.8 source tree. Depends on libgsf-1 (gsf_req).
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class AbiwordPluginEpubConan(ConanFile):
    name = "abiword-plugin-epub"
    version = "3.0.8"
    description = "AbiWord EPUB e-book export plugin"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/World/AbiWord"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # epub plugin needs libgsf-1 (gsf_req) per upstream plugin.m4
        self.requires("libgsf/1.14.53")

    def build_requirements(self):
        # AbiWord 的 git archive tarball 不带 configure/aclocal.m4/Makefile.in，
        # build() 必须跑 aclocal/autoconf/autoheader/automake 自举。
        # CI 沙箱(USER=100)对 $HOME/.local 手工安装的 automake 不可见(ENOENT)，
        # /data/service/hnp/bin 只有 autoconf 家族(777)没有 automake/libtool，
        # 故将 automake + libtool 作为 tool_requires 拉入(制品仓已发布 1.18/2.5.4，
        # 同 abiword-plugin-clarisworks 先例)。tool_requires 按 *build* profile
        # 解析，conan create 需同时传 -pr:h 与 -pr:b。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps: AbiWord 主 configure 用 PKG_CHECK_MODULES 发现
        # libgsf-1(epub plugin 依赖),必须生成依赖的 .pc 文件并注入 PKG_CONFIG_PATH
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # Enable only the epub plugin, disable all others
        tc.configure_args.append("--enable-plugins=epub")
        tc.configure_args.append("--disable-default-plugins")
        # Skip gtk checks for plugin-only build
        tc.configure_args.append("--with-gtk2=no")
        # OHOS 不被 config.guess 识别,显式传 --build/--host 跳 config.guess
        # (CI Worker 干净环境无本机 hack,必须写入配方)
        tc.configure_args.append("--build=aarch64-linux")
        tc.configure_args.append("--host=aarch64-linux")
        # AbiWord 主 configure 强依赖 png.h/jpeglib.h/链接 -ljpeg/-lpng(AC_MSG_ERROR),
        # libpng/libjpeg 未在制品仓发布时 CI 用 --build=missing 从源编译,
        # 注入 include+lib 路径供头检查与链接检查
        import glob as _glob
        _cpps = []
        _lds = []
        _png_incs = _glob.glob("/storage/Users/currentUser/.conan2/p/b/libpn*/p/include")
        if _png_incs:
            _cpps.append(_png_incs[0])
        _png_libs = _glob.glob("/storage/Users/currentUser/.conan2/p/b/libpn*/p/lib")
        if _png_libs:
            _lds.append(_png_libs[0])
        _jpeg_incs = _glob.glob("/storage/Users/currentUser/.conan2/p/b/libjp*/p/include")
        if _jpeg_incs:
            _cpps.append(_jpeg_incs[0])
        _jpeg_libs = _glob.glob("/storage/Users/currentUser/.conan2/p/b/libjp*/p/lib")
        if _jpeg_libs:
            _lds.append(_jpeg_libs[0])
        if _cpps:
            tc.configure_args.append("CPPFLAGS={}".format(
                " ".join("-I{}".format(i) for i in _cpps)))
        if _lds:
            tc.configure_args.append("LDFLAGS={}".format(
                " ".join("-L{}".format(i) for i in _lds)))
        # PkgConfigDeps 生成的 .pc 在 generators_folder,但 conanbuild env 未自动
        # 注入 PKG_CONFIG_PATH → 显式注入指向 generators_folder(含 libgsf-1.pc),
        # 否则 configure 的 PKG_CHECK_MODULES 报 "No package 'libgsf-1' found"。
        _gens = self.generators_folder
        tc.configure_args.append("PKG_CONFIG_PATH={}".format(_gens))
        # AbiWord 主 configure 强检全套 GUI 依赖(gtk+-3.0/cairo/pangocairo 等),
        # epub 插件仅需 libgsf/glib。configure 支持 DEPS_CFLAGS/DEPS_LIBS 预置
        # 绕过 pkg-config 检测,注入指向 libgsf/glib 的 include/lib 路径。
        import glob as _glob2
        _deps_cflags = []
        _deps_libs = []
        _gsf_incs = _glob2.glob("/storage/Users/currentUser/.conan2/p/b/libgs*/p/include/libgsf-1")
        if _gsf_incs:
            _deps_cflags.append("-I{}".format(_gsf_incs[0]))
        _gsf_libs = _glob2.glob("/storage/Users/currentUser/.conan2/p/b/libgs*/p/lib")
        if _gsf_libs:
            _deps_libs.append("-L{} -lgsf-1".format(_gsf_libs[0]))
        _glib_incs = _glob2.glob("/storage/Users/currentUser/.conan2/p/b/glib*/p/include/glib-2.0")
        if _glib_incs:
            _deps_cflags.append("-I{}".format(_glib_incs[0]))
        _glib_incs2 = _glob2.glob("/storage/Users/currentUser/.conan2/p/b/glib*/p/lib/glib-2.0/include")
        if _glib_incs2:
            _deps_cflags.append("-I{}".format(_glib_incs2[0]))
        _glib_libs = _glob2.glob("/storage/Users/currentUser/.conan2/p/b/glib*/p/lib")
        if _glib_libs:
            _deps_libs.append("-L{} -lglib-2.0 -lgobject-2.0".format(_glib_libs[0]))
        if _deps_cflags:
            tc.configure_args.append("DEPS_CFLAGS={}".format(" ".join(_deps_cflags)))
        if _deps_libs:
            tc.configure_args.append("DEPS_LIBS={}".format(" ".join(_deps_libs)))
        # AbiWord 主 configure 用 PKG_CHECK_MODULES 单独检查 glib-2.0/gthread-2.0/
        # gobject-2.0(PkgConfigDeps 因 glib 无 components 不生成这些 .pc),
        # configure 报 "No package 'glib-2.0' found" → 补写三个 .pc 指向 glib .a
        _glib_cands = []
        for _gp in _glob2.glob("/storage/Users/currentUser/.conan2/p/b/glib*/p"):
            if os.path.exists(os.path.join(_gp, "lib", "libgobject-2.0.a")):
                _glib_cands.append(_gp)
        if _glib_cands:
            _gl = _glib_cands[0]
            _inc = os.path.join(_gl, "include", "glib-2.0")
            _inc2 = os.path.join(_gl, "lib", "glib-2.0", "include")
            for _pcname, _libname in (("glib-2.0.pc", "glib-2.0"),
                                      ("gthread-2.0.pc", "gthread-2.0"),
                                      ("gobject-2.0.pc", "gobject-2.0")):
                _pf = os.path.join(self.generators_folder, _pcname)
                if not os.path.exists(_pf):
                    _pc = (
                        "prefix={}\n"
                        "libdir=${{prefix}}/lib\n"
                        "includedir=${{prefix}}/include/glib-2.0\n"
                        "includedir1=${{prefix}}/lib/glib-2.0/include\n"
                        "\n"
                        "Name: {}\n"
                        "Description: Conan package: {}\n"
                        "Version: 2.84.0\n"
                        "Libs: -L${{libdir}} {}/lib/lib{}.a\n"
                        "Cflags: -I${{includedir}} -I${{includedir1}}\n"
                        "Requires: glib-2.0\n"
                    ).format(_gl, _pcname.replace(".pc", ""),
                             _pcname.replace(".pc", ""), _gl, _libname)
                    with open(_pf, "w", encoding="utf-8") as _f:
                        _f.write(_pc)
        # AbiWord 主 configure 强依赖 boost(AX_BOOST_BASE 硬检查,报 'boost' not found),
        # epub 插件编译时 pd_Document.h 实际 include boost/shared_ptr.hpp →
        # stub boost 头提供 version.hpp(满足 configure 检查) + shared_ptr.hpp(编译用)
        _boost_stub = os.path.join(self.build_folder, "boost_stub")
        _boost_vh = os.path.join(_boost_stub, "boost", "version.hpp")
        if not os.path.exists(_boost_vh):
            os.makedirs(os.path.dirname(_boost_vh), exist_ok=True)
            with open(_boost_vh, "w", encoding="utf-8") as _f:
                _f.write("#ifndef BOOST_VERSION_HPP\n#define BOOST_VERSION_HPP\n"
                         "#define BOOST_VERSION 108300\n#define BOOST_LIB_VERSION \"1_83\"\n#endif\n")
        _boost_sp = os.path.join(_boost_stub, "boost", "shared_ptr.hpp")
        if not os.path.exists(_boost_sp):
            os.makedirs(os.path.dirname(_boost_sp), exist_ok=True)
            with open(_boost_sp, "w", encoding="utf-8") as _f:
                _f.write("#ifndef BOOST_SHARED_PTR_STUB_HPP\n#define BOOST_SHARED_PTR_STUB_HPP\n"
                         "#include <memory>\n"
                         "namespace boost {\n"
                         "using std::shared_ptr; using std::weak_ptr; using std::make_shared;\n"
                         "}\n#endif\n")
        tc.configure_args.append("CPPFLAGS=-I{} {}".format(
            _boost_stub, " ".join("-I{}".format(i) for i in _cpps) if _cpps else "").rstrip())
        # epub 插件编译需 AbiWord 主程序接口头(xap_Module.h/ut_string.h 等)
        # + libgsf 头(gsf/gsf-utils.h) + glib 头,注入源码 include + 依赖 include
        _src = self.source_folder
        _src_incs = [
            os.path.join(_src, "src", "af", "util", "xp"),
            os.path.join(_src, "src", "af", "util", "unix"),
            os.path.join(_src, "src", "wp", "impexp", "xp"),
            os.path.join(_src, "src", "af", "xap", "xp"),
            os.path.join(_src, "src", "af", "xap", "unix"),
            os.path.join(_src, "src", "af", "xap", "gtk"),
            os.path.join(_src, "src", "af", "gr", "xp"),
            os.path.join(_src, "src", "af", "ev", "xp"),
            os.path.join(_src, "src", "af", "ev", "gtk"),
            os.path.join(_src, "src", "text", "ptbl", "xp"),
            os.path.join(_src, "src", "text", "fmt", "xp"),
            os.path.join(_src, "src", "wp", "ap", "xp"),
            os.path.join(_src, "src", "wp", "ap", "gtk"),
        ]
        _src_incs = [i for i in _src_incs if os.path.isdir(i)]
        import glob as _glob3
        for _g in _glob3.glob("/storage/Users/currentUser/.conan2/p/b/libgs*/p/include/libgsf-1"):
            if _g not in _src_incs:
                _src_incs.append(_g)
        for _g in _glob3.glob("/storage/Users/currentUser/.conan2/p/b/glib*/p/include/glib-2.0"):
            if _g not in _src_incs:
                _src_incs.append(_g)
        for _g in _glob3.glob("/storage/Users/currentUser/.conan2/p/b/glib*/p/lib/glib-2.0/include"):
            if _g not in _src_incs:
                _src_incs.append(_g)
        for _g in _glob3.glob("/storage/Users/currentUser/.conan2/p/b/libxm*/p/include/libxml2"):
            if _g not in _src_incs:
                _src_incs.append(_g)
        for _g in _glob3.glob("/storage/Users/currentUser/.conan2/p/b/fribi*/p/include/fribidi"):
            if _g not in _src_incs:
                _src_incs.append(_g)
        # config.h 定义 TOOLKIT_GTK_ALL 1(即使 --with-gtk2=no),ut_misc.h/ut_unixColor.h
        # 走 gtk 分支 #include <gtk/gtk.h> 与 <gdk/gdk.h> → 用 gtk/gdk stub 头
        # (同 boost stub 思路),仅定义 GtkWidget/GdkColor/GdkRGBA 等类型供
        # AbiNativeWidget typedef 与颜色转换声明,epub 插件不需真 gtk/gdk。
        _gtk_stub = os.path.join(self.build_folder, "gtk_stub")
        _gtk_vh = os.path.join(_gtk_stub, "gtk", "gtk.h")
        if not os.path.exists(_gtk_vh):
            os.makedirs(os.path.dirname(_gtk_vh), exist_ok=True)
            with open(_gtk_vh, "w", encoding="utf-8") as _f:
                _f.write("#ifndef GTK_STUB_H\n#define GTK_STUB_H\n"
                         "typedef struct _GtkWidget GtkWidget;\n#endif\n")
        _gdk_vh = os.path.join(_gtk_stub, "gdk", "gdk.h")
        if not os.path.exists(_gdk_vh):
            os.makedirs(os.path.dirname(_gdk_vh), exist_ok=True)
            with open(_gdk_vh, "w", encoding="utf-8") as _f:
                _f.write("#ifndef GDK_STUB_H\n#define GDK_STUB_H\n"
                         "typedef struct _GdkColor { unsigned int red, green, blue; } GdkColor;\n"
                         "typedef struct _GdkRGBA { double r, g, b, a; } GdkRGBA;\n"
                         "#define GTK_CHECK_VERSION(maj, min, mic) 0\n"
                         "#endif\n")
        _src_incs.append(_gtk_stub)
        if _src_incs:
            tc.configure_args.append("CXXFLAGS={}".format(
                " ".join("-I{}".format(i) for i in _src_incs)))
        tc.generate()

    def build(self):
        # Generate configure from configure.ac (no pre-generated configure)
        self._run_autogen()

        # Patch config.guess/config.sub for OHOS
        self._patch_config_for_ohos()

        apply_conandata_patches(self)

        autotools = Autotools(self)
        autotools.configure()
        # epub 插件的 dialogs/ 子目录是导出选项 GUI(ap_UnixDialog_EpubExportOptions.cpp
        # 用 GTK_DIALOG/GTK_TOGGLE_BUTTON 等真 gtk API),插件核心导入导出逻辑在
        # common/imp/exp。本机/CI 无 gtk → patch 生成的 Makefile 移除 dialogs
        # (am__append_1/2 为空,SUBDIRS 与 epub_la_LIBADD 不含 dialogs)。
        # 注意: self.build_folder 已是 .../b/build-release,勿再拼 build-release。
        _epub_mf = os.path.join(self.build_folder, "plugins", "epub", "Makefile")
        if os.path.exists(_epub_mf):
            with open(_epub_mf, "r", encoding="utf-8") as _f:
                _mf = _f.read()
            _changed = False
            for _pat, _rep in (("am__append_1 = dialogs\n", "am__append_1 =\n"),
                               ("am__append_2 = dialogs/libdialogs.la\n", "am__append_2 =\n")):
                if _pat in _mf:
                    _mf = _mf.replace(_pat, _rep)
                    _changed = True
            if _changed:
                with open(_epub_mf, "w", encoding="utf-8") as _f:
                    _f.write(_mf)
                self.output.info("  [ok] Patched plugins/epub/Makefile: removed dialogs subdir (no gtk)")
            else:
                self.output.warning("  [warn] dialogs markers not found in plugins/epub/Makefile")
        # Build the plugin subdirectory only
        # 注意: 不能用 `make -C plugins/epub` 递归——HMDFS 下 make 递归子目录时
        # libtool 解析相对 LIBADD(xp/libxp.la)需要 pwd/getcwd,但 getcwd 失败
        # (cannot access parent directories)导致 'cannot determine absolute
        # directory name of xp'。改为 cd 进插件目录再 make,由 bash 维护 PWD
        # 环境变量,libtool 的 pwd 走 $PWD 而非 getcwd → 绕开该限制。
        # self.build_folder 已是 .../b/build-release,勿再拼 build-release。
        _epub_dir = os.path.join(self.build_folder, "plugins", "epub")
        self.run("cd {} && make".format(_epub_dir), env="conanbuild")

    def _run_autogen(self):
        """Run autogen.sh to generate configure and plugin configuration files.

        OHOS HMDFS 环境下 autoreconf 链存在 autoconf.m4f 加载冲突
        (AC_DEFINE/AC_MSG_ERROR 等基础宏报"未定义",实为 warning 被
        当 hard error),改用 autoconf + automake 直跑链绕过(同 eml 配方)。
        """
        import shutil

        self.output.info("Running autogen-common.sh to generate plugin configuration...")
        # 用 self.run(env="conanbuild") 而非裸 subprocess.run: tool_requires
        # (automake/libtool) 注入的 PATH/ACLOCAL_PATH/PERL5LIB 只对 conan build
        # 环境生效, CI 沙箱原始 PATH 找不到 aclocal(ENOENT)。
        self.run(
            "bash autogen-common.sh",
            cwd=self.source_folder,
            env="conanbuild",
        )

        # 先跑 aclocal 生成 aclocal.m4(提供 AM_* 宏)
        self.output.info("Running aclocal to generate aclocal.m4...")
        self.run(
            "aclocal --force",
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,  # aclocal 有 warning 不影响
        )

        # autoconf 直接编译 configure.ac → configure(绕 autoreconf 链冲突)
        self.output.info("Running autoconf to generate configure...")
        self.run(
            "autoconf -o configure configure.ac",
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,  # AC_DEFINE 等 warning 非硬错,configure 仍生成
        )
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise ConanException("autoconf failed to generate configure")

        # autoheader 生成 config.h.in
        self.output.info("Running autoheader to generate config.h.in...")
        self.run(
            "autoheader",
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,
        )
        _cfg_h_in = os.path.join(self.source_folder, "config.h.in")
        if not os.path.exists(_cfg_h_in):
            # autoheader 无输出时 touch 兜底
            open(_cfg_h_in, "w").close()

        # ltmain.sh 必须先于 automake 补齐,否则 automake 报
        # "required file './ltmain.sh' not found" 而不生成 Makefile.in
        _ltmain = os.path.join(self.source_folder, "ltmain.sh")
        if not os.path.exists(_ltmain):
            # 优先从 tool_requires 的 libtool 包取 build-aux/ltmain.sh
            # (CI 沙箱 PATH 无 libtool, shutil.which 会 miss)
            _lt_src = ""
            try:
                _lt_pkg = self.dependencies["libtool"].package_folder
                if _lt_pkg:
                    _cand = os.path.join(_lt_pkg, "share", "libtool", "build-aux", "ltmain.sh")
                    if os.path.exists(_cand):
                        _lt_src = _cand
            except Exception:
                pass
            if not _lt_src:
                _libtool_aux = os.path.join(
                    os.path.dirname(shutil.which("libtool") or ""),
                    "..", "share", "libtool", "build-aux", "ltmain.sh"
                )
                if os.path.exists(_libtool_aux):
                    _lt_src = _libtool_aux
            if _lt_src:
                shutil.copy(_lt_src, _ltmain)
                self.output.info("  [ok] Copied ltmain.sh from libtool build-aux")
            else:
                self.output.warning("  [warn] ltmain.sh not found, libtool macros may fail")

        # automake 补 Makefile.in + install-sh 等(--add-missing)
        self.output.info("Running automake to generate Makefile.in...")
        self.run(
            "automake --add-missing --copy --no-force",
            cwd=self.source_folder,
            env="conanbuild",
            ignore_errors=True,  # 部分 Makefile.am 有 GNU make 扩展 warning
        )

    def _patch_config_for_ohos(self):
        """Patch config.guess and config.sub for OHOS (R15).

        Prefer the skill's Perl script; fall back to manual Python patching
        (mirrors addrwatch/nspr/slang) so OHOS triplet is recognized even
        when OHC_SKILL_ROOT is unset or the Perl script is absent.
        """
        skill_root = os.environ.get("OHC_SKILL_ROOT", "")
        if skill_root:
            script = os.path.join(skill_root, "scripts", "patch-autotools-ohos.pl")
            if os.path.exists(script):
                self.output.info("Patching config.guess/config.sub with skill script")
                for f in ("config.guess", "config.sub"):
                    path = os.path.join(self.source_folder, f)
                    if os.path.exists(path):
                        subprocess.run(["perl", script, path], check=True)
                return

        # Fallback: manual Python patching
        self.output.info("OHC_SKILL_ROOT/Perl script unavailable, falling back to manual Python patch")
        cg_path = os.path.join(self.source_folder, "config.guess")
        cs_path = os.path.join(self.source_folder, "config.sub")
        if os.path.exists(cg_path):
            self._manual_patch_config_guess(cg_path)
        else:
            self.output.warning("config.guess not found, skipping guess patch")
        if os.path.exists(cs_path):
            self._manual_patch_config_sub(cs_path)
        else:
            self.output.warning("config.sub not found, skipping sub patch")

    def _manual_patch_config_guess(self, cg_path):
        """Manually patch config.guess for HarmonyOS detection."""
        with open(cg_path, "r") as f:
            content = f.read()

        changed = False

        # 1. Add __OHOS__ LIBC detection after __ANDROID__
        if "__OHOS__" not in content:
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            new = "#if defined(__ANDROID__)\n    LIBC=android\n#elif defined(__OHOS__)\n    LIBC=ohos"
            if old in content:
                content = content.replace(old, new, 1)
                changed = True
                self.output.info("  [ok] Added __OHOS__ LIBC detection to config.guess")
            else:
                self.output.warning("  [warn] Could not find __ANDROID__/LIBC=android in config.guess")

        # 2. Add HarmonyOS case block before NetBSD
        if "HarmonyOS" not in content:
            block = (
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                '\t    i?86)          MACHINE=i686 ;;\n'
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                '\tesac\n'
                '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                '\t;;\n\n'
                '    *:NetBSD:*:*)'
            )
            if "    *:NetBSD:*:*)" in content:
                content = content.replace("    *:NetBSD:*:*)", block, 1)
                changed = True
                self.output.info("  [ok] Added HarmonyOS system identification to config.guess")
            else:
                self.output.warning("  [warn] Could not find NetBSD insertion point in config.guess")

        if changed:
            with open(cg_path, "w") as f:
                f.write(content)

    def _manual_patch_config_sub(self, cs_path):
        """Manually patch config.sub for ohos-linux support."""
        with open(cs_path, "r") as f:
            content = f.read()

        changed = False

        # 1. Add ohos-linux triplet after android-linux
        if "ohos-linux" not in content:
            import re
            pattern = r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown\s*\n\s*basic_os=linux-android\s*\n\s*;;\s*\n)'
            replacement = r'\1\tohos-linux)\n\tbasic_machine=$field1-unknown\n\tbasic_os=linux-ohos\n\t;;\n'
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                changed = True
                self.output.info("  [ok] Added ohos-linux triplet to config.sub")
            else:
                self.output.warning("  [warn] Could not find android-linux in config.sub")

        # 2. Add ohos* to OS type list
        if "ohos*" not in content:
            content = content.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
            changed = True
            self.output.info("  [ok] Added ohos* to OS list in config.sub")

        # 3. Add linux-ohos to kernel-OS validation list
        # 注意:linux-ohos) 不带尾通配 * —— 避免 linux-ohos-android 等不该归入 ohos 的三元组被误匹配
        # 正则: 在 linux-uclibc* 之后、')' 之前插入 ' | linux-ohos' ——
        # 若追加到 ')' 之后会得到 'linux-uclibc* )| linux-ohos)' 导致 shell 语法错误
        if "linux-ohos)" not in content:
            import re
            content, count = re.subn(r'(linux-uclibc[\*/-]?\s*)(\))', r'\1| linux-ohos\2', content)
            if count > 0:
                changed = True
                self.output.info("  [ok] Added linux-ohos to kernel list in config.sub")
            else:
                self.output.warning("  [warn] Could not find linux-uclibc pattern in config.sub")

        if changed:
            with open(cs_path, "w") as f:
                f.write(content)

    def package(self):
        # Copy the plugin .so to the package folder via glob + copy.
        # 不用 autotools.install(target=...)：Conan 2.x 的 install/make 不追加
        # DESTDIR，配合 configure 阶段 --prefix=/ 会把 .so 装到系统目录(/lib/)
        # 而非 Conan 包目录，在非 root CI worker 上会因无写权限失败。
        # glob + copy 直接从 build_folder/.libs/ 取产物到 package_folder，正确且幂等。
        import glob
        for so in glob.glob(os.path.join(self.build_folder, "plugins", "epub", ".libs", "*.so*")):
            dst = os.path.join(self.package_folder, "lib", "abiword", "plugins")
            os.makedirs(dst, exist_ok=True)
            copy(self, os.path.basename(so), os.path.dirname(so), dst)

    def package_info(self):
        self.cpp_info.libs = []
        # Set the plugin directory for discovery
        self.runenv_info.define_path("ABIWORD_PLUGINS_DIR",
            os.path.join(self.package_folder, "lib", "abiword", "plugins"))
