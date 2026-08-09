#!/usr/bin/env python3
"""Conan recipe — abiword-plugin-eml 3.0.8

AbiWord EML (Outlook Express Email) export plugin.
Part of the AbiWord 3.0.8 source tree.
"""
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class AbiwordPluginEmlConan(ConanFile):
    name = "abiword-plugin-eml"
    version = "3.0.8"
    description = "AbiWord EML (Outlook Express Email) export plugin"
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
        # AbiWord 主 configure 强检 libgsf-1 >= 1.14.18(PKG_CHECK_MODULES),
        # eml 插件亦需 libgsf 处理 MIME/OLE 附件,必须声明依赖
        self.requires("libgsf/1.14.53")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PkgConfigDeps: AbiWord 主 configure 用 PKG_CHECK_MODULES 发现
        # libgsf-1/glib 等依赖,必须生成依赖的 .pc 文件并注入 PKG_CONFIG_PATH
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # Enable only the eml plugin, disable all others
        tc.configure_args.append("--enable-plugins=eml")
        tc.configure_args.append("--disable-default-plugins")
        # Skip gtk checks for plugin-only build
        tc.configure_args.append("--with-gtk2=no")
        # OHOS 不被 config.guess 识别,显式传 --build/--host 跳 config.guess
        tc.configure_args.append("--build=aarch64-linux")
        tc.configure_args.append("--host=aarch64-linux")
        # AbiWord 主 configure 强依赖 png.h/jpeglib.h/boost(AX_BOOST_BASE 硬检查),
        # libpng/libjpeg 未在制品仓发布时 CI 用 --build=missing 从源编译,
        # boost 用 stub version.hpp(eml 插件本身不 include boost 头)满足检查;
        # 注入 include+lib 路径供 pkg-config/头检查/链接检查
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
        # boost stub(eml 插件不用 boost,仅满足 AbiWord 主 configure 的 AX_BOOST_BASE 检查)
        _boost_stub = os.path.join(self.build_folder, "boost_stub")
        _boost_vh = os.path.join(_boost_stub, "boost", "version.hpp")
        if not os.path.exists(_boost_vh):
            os.makedirs(os.path.dirname(_boost_vh), exist_ok=True)
            with open(_boost_vh, "w", encoding="utf-8") as _f:
                _f.write("#ifndef BOOST_VERSION_HPP\n#define BOOST_VERSION_HPP\n"
                         "#define BOOST_VERSION 108300\n#define BOOST_LIB_VERSION \"1_83\"\n#endif\n")
        _cpps.append(_boost_stub)
        if _cpps:
            tc.configure_args.append("CPPFLAGS={}".format(
                " ".join("-I{}".format(i) for i in _cpps)))
        if _lds:
            tc.configure_args.append("LDFLAGS={}".format(
                " ".join("-L{}".format(i) for i in _lds)))
        # PkgConfigDeps 生成的 .pc 在 generators_folder,但 conanbuild env 未自动
        # 注入 PKG_CONFIG_PATH,configure 的 PKG_CHECK_MODULES 找不到 libgsf-1。
        # 显式注入 PKG_CONFIG_PATH 指向 generators_folder(含 libgsf-1.pc 等)。
        _gens = self.generators_folder
        tc.configure_args.append("PKG_CONFIG_PATH={}".format(_gens))
        # AbiWord 主 configure 用 PKG_CHECK_MODULES 单独检查 glib-2.0/gthread-2.0/
        # gobject-2.0(PkgConfigDeps 因 glib 无 components 且经 libgsf 传递依赖,
        # 未生成 glib-2.0.pc),configure 报 "No package 'glib-2.0' found"
        # (CI 实测)。补写 glib-2.0.pc 本体(探测 glib 包目录) + 从它派生
        # gobject/gthread .pc(同 libgsf 修复)。
        import glob as _glob
        _glib_root = None
        for _gp in _glob.glob("/storage/Users/currentUser/.conan2/p/b/glib*/p"):
            if os.path.isdir(os.path.join(_gp, "include", "glib-2.0")):
                _glib_root = _gp
                break
        _glib_pc_src = os.path.join(_gens, "glib-2.0.pc")
        _glib_pc_cflags = "-I${includedir} -I${includedir1}"
        if os.path.exists(_glib_pc_src):
            with open(_glib_pc_src, "r", encoding="utf-8", errors="ignore") as _f:
                _glib_pc_text = _f.read()
            _m = re.search(r"^Cflags:\s*(.+)$", _glib_pc_text, re.M)
            if _m:
                _glib_pc_cflags = _m.group(1).strip()
        # glib-2.0.pc 本体(缺失时补写: Requires 链的根,不写则 gthread/gobject
        # 的 Requires: glib-2.0 解析失败 → configure 报 No package 'glib-2.0')
        if not os.path.exists(_glib_pc_src) and _glib_root:
            _pc_text = (
                "prefix={}\n"
                "libdir=${{prefix}}/lib\n"
                "includedir=${{prefix}}/include/glib-2.0\n"
                "includedir1=${{prefix}}/lib/glib-2.0/include\n"
                "\n"
                "Name: glib-2.0\n"
                "Description: Conan package: glib-2.0\n"
                "Version: 2.84.0\n"
                "Libs: -L${{libdir}} -lglib-2.0\n"
                "Cflags: -I${{includedir}} -I${{includedir1}}\n"
            ).format(_glib_root)
            with open(_glib_pc_src, "w", encoding="utf-8") as _f:
                _f.write(_pc_text)
        for _pcname, _libname in (("gobject-2.0.pc", "gobject-2.0"),
                                  ("gthread-2.0.pc", "gthread-2.0")):
            _pf = os.path.join(_gens, _pcname)
            if not os.path.exists(_pf):
                _pc_text = (
                    "prefix=${{pcfiledir}}/../..\n"
                    "libdir=${{prefix}}/lib\n"
                    "includedir=${{prefix}}/include/glib-2.0\n"
                    "includedir1=${{prefix}}/lib/glib-2.0/include\n"
                    "\n"
                    "Name: {}\n"
                    "Description: Conan package: {}\n"
                    "Version: 2.84.0\n"
                    "Libs: -L${{libdir}} -l{}\n"
                    "Cflags: {}\n"
                    "Requires: glib-2.0\n"
                ).format(_pcname.replace(".pc", ""), _pcname.replace(".pc", ""),
                         _libname, _glib_pc_cflags)
                with open(_pf, "w", encoding="utf-8") as _f:
                    _f.write(_pc_text)
        # AbiWord 主 configure 强检全套 GUI 依赖(gtk+-3.0/cairo/pangocairo 等),
        # eml 插件仅需 libgsf/glib。configure 支持 DEPS_CFLAGS/DEPS_LIBS 预置
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
        # eml 插件编译需 AbiWord 主程序接口头(ut_string/ut_assert/ie_exp_Text/xap_Module),
        # 且 ie_types.h 需 glib.h,注入源码 include + glib include 目录到 CXXFLAGS
        _src = self.source_folder
        _src_incs = [
            os.path.join(_src, "src", "af", "util", "xp"),
            os.path.join(_src, "src", "wp", "impexp", "xp"),
            os.path.join(_src, "src", "af", "xap", "xp"),
            os.path.join(_src, "src", "af", "xap", "unix"),
            os.path.join(_src, "src", "text", "ptbl", "xp"),
            os.path.join(_src, "src", "text", "fmt", "xp"),
        ]
        _src_incs = [i for i in _src_incs if os.path.isdir(i)]
        # glib 头目录(ie_types.h 需 glib.h)也注入
        import glob as _glob3
        for _g in _glob3.glob("/storage/Users/currentUser/.conan2/p/b/glib*/p/include/glib-2.0"):
            if _g not in _src_incs:
                _src_incs.append(_g)
        for _g in _glob3.glob("/storage/Users/currentUser/.conan2/p/b/glib*/p/lib/glib-2.0/include"):
            if _g not in _src_incs:
                _src_incs.append(_g)
        # libgsf 头目录(ut_go_file.h 需 gsf/gsf.h)也注入
        for _g in _glob3.glob("/storage/Users/currentUser/.conan2/p/b/libgs*/p/include/libgsf-1"):
            if _g not in _src_incs:
                _src_incs.append(_g)
        # libxml2 头目录(gsf-libxml.h 需 libxml/parser.h)也注入
        for _g in _glob3.glob("/storage/Users/currentUser/.conan2/p/b/libxm*/p/include/libxml2"):
            if _g not in _src_incs:
                _src_incs.append(_g)
        # fribidi 头目录(ut_string.h 需 <fribidi.h>,头在 include/fribidi/ 子目录)也注入
        for _g in _glob3.glob("/storage/Users/currentUser/.conan2/p/b/fribi*/p/include/fribidi"):
            if _g not in _src_incs:
                _src_incs.append(_g)
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
        # Build the plugin subdirectory only
        autotools.make(target="-C plugins/eml")

    def _run_autogen(self):
        """Run autogen.sh to generate configure and plugin configuration files.

        OHOS HMDFS 环境下 autoreconf 链存在 autoconf.m4f 加载冲突
        (AC_DEFINE/AC_MSG_ERROR 等基础宏报"未定义",实为 warning 被
        当 hard error),改用 autoconf + automake 直跑链绕过。
        """
        import shutil

        self.output.info("Running autogen-common.sh to generate plugin configuration...")
        subprocess.run(
            ["bash", "autogen-common.sh"],
            cwd=self.source_folder,
            check=True,
        )

        # 先跑 aclocal 生成 aclocal.m4(提供 AM_* 宏)
        self.output.info("Running aclocal to generate aclocal.m4...")
        subprocess.run(
            ["aclocal", "--force"],
            cwd=self.source_folder,
            check=False,  # aclocal 有 warning 不影响
        )

        # autoconf 直接编译 configure.ac → configure(绕 autoreconf 链冲突)
        self.output.info("Running autoconf to generate configure...")
        subprocess.run(
            ["autoconf", "-o", "configure", "configure.ac"],
            cwd=self.source_folder,
            check=False,  # AC_DEFINE 等 warning 非硬错,configure 仍生成
        )
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise ConanException("autoconf failed to generate configure")

        # autoheader 生成 config.h.in
        self.output.info("Running autoheader to generate config.h.in...")
        subprocess.run(
            ["autoheader"],
            cwd=self.source_folder,
            check=False,
        )
        _cfg_h_in = os.path.join(self.source_folder, "config.h.in")
        if not os.path.exists(_cfg_h_in):
            # autoheader 靡输出时 touch 兜底
            open(_cfg_h_in, "w").close()

        # automake 补 Makefile.in + install-sh 等(--add-missing)
        # 注意: ltmain.sh 必须先于 automake 补齐,否则 automake 报
        # "required file './ltmain.sh' not found" 而不生成 Makefile.in
        _ltmain = os.path.join(self.source_folder, "ltmain.sh")
        if not os.path.exists(_ltmain):
            _libtool_aux = os.path.join(
                os.path.dirname(shutil.which("libtool") or ""),
                "..", "share", "libtool", "build-aux", "ltmain.sh"
            )
            if os.path.exists(_libtool_aux):
                shutil.copy(_libtool_aux, _ltmain)
                self.output.info("  [ok] Copied ltmain.sh from libtool build-aux")
            else:
                self.output.warning("  [warn] ltmain.sh not found, libtool macros may fail")
        self.output.info("Running automake to generate Makefile.in...")
        subprocess.run(
            ["automake", "--add-missing", "--copy", "--no-force"],
            cwd=self.source_folder,
            check=False,  # 部分 Makefile.am 有 GNU make 扩展 warning
        )

    def _patch_config_for_ohos(self):
        """Patch config.guess and config.sub for OHOS (R15)."""
        # Check if the skill's perl script is available
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

        self.output.info("OHC_SKILL_ROOT not set or script not found, skipping autotools patch")

    def package(self):
        # Copy the plugin .so to the package folder via glob + copy.
        # 不用 autotools.make(target="... install")：Conan 2.x 的 make() 不追加
        # DESTDIR，配合 configure 阶段 --prefix=/ 会把 .so 装到系统目录(/lib/)
        # 而非 Conan 包目录，在非 root CI worker 上会因无写权限失败。
        # glob + copy 直接从 build_folder/.libs/ 取产物到 package_folder，正确且幂等。
        import glob
        for so in glob.glob(os.path.join(self.build_folder, "plugins", "eml", ".libs", "*.so*")):
            dst = os.path.join(self.package_folder, "lib", "abiword", "plugins")
            os.makedirs(dst, exist_ok=True)
            copy(self, os.path.basename(so), os.path.dirname(so), dst)

    def package_info(self):
        self.cpp_info.libs = []
        # Set the plugin directory for discovery
        self.runenv_info.define_path("ABIWORD_PLUGINS_DIR",
            os.path.join(self.package_folder, "lib", "abiword", "plugins"))