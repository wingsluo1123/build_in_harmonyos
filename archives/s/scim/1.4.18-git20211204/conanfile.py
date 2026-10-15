#!/usr/bin/env python3
"""Conan recipe for scim 1.4.18-git20211204 (Smart Common Input Method).

The upstream git snapshot omits generated Autotools files; the recipe runs
the bundled bootstrap script (autopoint + intltoolize + autoreconf) first.

Two source patches are applied:
  1. configure.ac  -- override AS_TMPDIR so config.status uses umask 002.
     HMDFS maps directory owners to a fixed uid; 0700 temp dirs created with
     umask 077 are not writable by the build process (E052/E060).
  2. m4/pkg.m4    -- the upstream tarball lacks pkg.m4; without it the
     PKG_PROG_PKG_CONFIG macro stays unexpanded and configure fails.

The GTK Panel (extras/panel) is disabled: upstream 1.4.18 code is not
GTK3-clean (scim_panel_gtk.cpp fails with 20 errors on gtk3).  The consumer
(scim-thai) only needs the core libscim + scim.pc and the optional
scim-gtkutils library.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class ScimConan(ConanFile):
    name = "scim"
    version = "1.4.18-git20211204"
    description = "Smart Common Input Method platform (SCIM)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/scim-im/scim"
    url = "https://github.com/scim-im/scim"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    package_type = "library"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)
        # The upstream git snapshot omits pkg.m4 (PKG_PROG_PKG_CONFIG) and
        # intltool.m4 (IT_PROG_INTLTOOL); ship them beside the recipe so the
        # source tree gets them before bootstrap (same pattern as abiword).
        macro_dir = os.path.join(self.recipe_folder, "m4")
        if os.path.isdir(macro_dir):
            shutil.copytree(
                macro_dir,
                os.path.join(self.export_sources_folder, "m4"),
                dirs_exist_ok=True,
            )
        # gettext's AM_GNU_GETTEXT macro makes automake require ./config.rpath
        # in the source tree; the conan gettext/0.22.5 package ships only
        # libintl.h/libintl.a/share/locale (no data files), so the clean CI
        # environment fails with "required file './config.rpath' not found".
        # Provide the gettext data script beside the recipe (same pattern).
        config_rpath = os.path.join(self.recipe_folder, "config.rpath")
        if os.path.isfile(config_rpath):
            shutil.copy2(
                config_rpath,
                os.path.join(self.export_sources_folder, "config.rpath"))

    def requirements(self):
        # LT_INIT([dlopen]) resolves libltdl from the system path.
        self.requires("libltdl/2.6.0")
        # scim-gtkutils (used by the optional scim-thai setup module) needs GTK3.
        self.requires("gtk/3.24.38")

    def build_requirements(self):
        # The git snapshot has no configure; bootstrap needs the full stack.
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        # gettext/0.22.5 ships only libintl (no bin tools); intltool.m4's
        # IT_PROG_INTLTOOL hard-requires xgettext/msgmerge/msgfmt and the HNP
        # toolchain lacks msgmerge, so the clean CI env failed configure with
        # "GNU gettext tools not found; required for intltool".  Upgrade to
        # 0.22.5.1 which packages the full bin tools (msgmerge/msgfmt/xgettext)
        # plus share/aclocal macros and share/gettext/config.rpath; the
        # VirtualBuildEnv then puts them on PATH during bootstrap.
        self.tool_requires("gettext/0.22.5.1")
        self.tool_requires("intltool/0.51.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = PkgConfigDeps(self)
        deps.generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # GTK Panel code is not GTK3-clean upstream (20 compile errors);
            # the consumer (scim-thai) does not need it.
            "--disable-panel-gtk",
            "--enable-tests",
        ])
        # LT_INIT([dlopen]) probes ltdl.h/-lltdl directly (not pkg-config);
        # expose dependency include/lib dirs so configure resolves the system
        # libltdl instead of falling back to the in-tree libltdlc.la.
        includes, libdirs = self._dependency_paths()
        if includes:
            tc.configure_args.append("CPPFLAGS=" + " ".join(
                f"-I{path}" for path in includes))
        if libdirs:
            tc.configure_args.append("LDFLAGS=" + " ".join(
                f"-L{path}" for path in libdirs))
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-linux",
                "--host=aarch64-linux",
            ])
        tc.generate()

        if str(self.settings.os) == "OHOS":
            tools = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
            compiler = tools.get("c", "clang")
            tool_dir = os.path.dirname(compiler)
            env = Environment()
            env.prepend_path("PATH", tool_dir)
            # HNP cmake/clang are libc++ built; their libc++.so lives in the
            # OHOS SDK <llvm>/lib/aarch64-linux-ohos/ which the profile does
            # not add to LD_LIBRARY_PATH.  Without it test_package's
            # cmake.configure() dies with "_ZNSt4__n1... symbol not found".
            # tool_dir/bin entries are symlinks into the SDK; resolve the real
            # clang to locate <llvm>/lib/aarch64-linux-ohos.
            real_clang = os.path.realpath(compiler)
            llvm_lib = os.path.join(
                os.path.dirname(os.path.dirname(real_clang)), "lib",
                "aarch64-linux-ohos")
            if os.path.isdir(llvm_lib):
                env.append_path("LD_LIBRARY_PATH", llvm_lib)
            for variable, executable in {
                "LD": "ld.lld",
                "AR": "llvm-ar",
                "NM": "llvm-nm",
                "RANLIB": "llvm-ranlib",
                "STRIP": "llvm-strip",
                "OBJDUMP": "llvm-objdump",
            }.items():
                path = os.path.join(tool_dir, executable)
                if os.path.exists(path):
                    env.define_path(variable, path)
            # autoreconf/intltoolize are perl scripts; the tool_requires perl
            # package injects PERL5LIB pointing at its own 5.42.2 XS modules,
            # which the system perl 5.42.0 interpreter cannot dlopen
            # (Perl_my_cxt_init: symbol not found).  Pin PERL to the HNP perl
            # and restrict PERL5LIB to the automake package's pure-perl module
            # dir (Automake::Config) so aclocal can load it without pulling in
            # the mismatched XS modules.
            system_perl = os.path.join(tool_dir, "perl")
            if os.path.exists(system_perl):
                env.define_path("PERL", system_perl)
            automake = self.dependencies.build["automake"]
            automake_share = os.path.join(
                automake.package_folder, "share", "automake-1.18")
            env.define_path("PERL5LIB", automake_share)
            # The conan intltoolize hardcodes prefix=/ (configure substitute
            # gone wrong), so its pkgdatadir resolves to //share/intltool and
            # the Makefile.in.in template cannot be found.  CI runs in a clean
            # environment where only the conan intltoolize exists (no system
            # intltool), so generate a fixed copy with prefix pointed at the
            # package folder and prepend its dir to PATH.
            intltool = self.dependencies.build["intltool"]
            intltoolize_src = os.path.join(
                intltool.package_folder, "bin", "intltoolize")
            fix_dir = os.path.join(self.build_folder, "intltoolize-fix")
            os.makedirs(fix_dir, exist_ok=True)
            intltoolize_fixed = os.path.join(fix_dir, "intltoolize")
            with open(intltoolize_src, "r", encoding="utf-8",
                      errors="replace") as handle:
                script = handle.read()
            # Replace the hardcoded "prefix=/" from the Directory names block
            # (first occurrence) with the package folder.
            script = script.replace(
                "prefix=/", "prefix=" + intltool.package_folder, 1)
            with open(intltoolize_fixed, "w", encoding="utf-8") as handle:
                handle.write(script)
            os.chmod(intltoolize_fixed, 0o755)
            env.prepend_path("PATH", fix_dir)
            env.vars(self).save_script("scim_linker_env")

    def _dependency_paths(self):
        """Collect include/lib dirs of all direct dependencies so the
        autotools configure can find system libltdl (LT_INIT dlopen probes
        ltdl.h + -lltdl directly, not via pkg-config)."""
        includes = []
        libdirs = []
        for dep in self.dependencies.values():
            package_folder = getattr(dep, "package_folder", None)
            if not package_folder:
                continue
            for include in dep.cpp_info.includedirs:
                includes.append(include if os.path.isabs(include)
                                else os.path.join(package_folder, include))
            for libdir in dep.cpp_info.libdirs:
                libdirs.append(libdir if os.path.isabs(libdir)
                               else os.path.join(package_folder, libdir))
        return includes, libdirs

    def _stage_libtool_data(self):
        """Copy complete libltdl source + build-aux + m4 macros to a writable
        staging dir and point libtoolize at it via the _lt_pkgdatadir env var.

        The OHOS-conan libtool relocation leaves only headers under
        share/libtool-conan/libltdl/ while the full libltdl source tree lives
        under share/libtool/ (COPYING.LIB, configure.ac, Makefile.am, lt_*.c,
        loaders/, ...).  libtoolize (LT_INIT dlopen) requires that full tree to
        regenerate the in-tree libltdl/ subproject (E443 pattern).
        """
        libtool_root = self.dependencies.build["libtool"].package_folder
        pkgdatadir = os.path.join(
            self.build_folder, "scim-libtool-data-" + os.path.basename(self.build_folder))
        for subdir in ("build-aux", "m4", "libltdl"):
            os.makedirs(os.path.join(pkgdatadir, subdir), exist_ok=True)

        source_aux = os.path.join(libtool_root, "share", "libtool", "build-aux")
        for filename in os.listdir(source_aux):
            shutil.copy2(
                os.path.join(source_aux, filename),
                os.path.join(pkgdatadir, "build-aux", filename))

        source_m4 = os.path.join(libtool_root, "share", "aclocal")
        for filename in os.listdir(source_m4):
            if filename.endswith(".m4"):
                shutil.copy2(
                    os.path.join(source_m4, filename),
                    os.path.join(pkgdatadir, "m4", filename))

        # Full libltdl source lives at the top level of share/libtool/.
        source_ltdl = os.path.join(libtool_root, "share", "libtool")
        for filename in os.listdir(source_ltdl):
            src = os.path.join(source_ltdl, filename)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(pkgdatadir, "libltdl", filename))
        # libtoolize also expects the header subdir libltdl/libltdl/*.h
        # (lt__alloc.h, lt_dlloader.h, ...) beside the top-level sources.
        source_ltdl_headers = os.path.join(source_ltdl, "libltdl")
        if os.path.isdir(source_ltdl_headers):
            shutil.copytree(
                source_ltdl_headers,
                os.path.join(pkgdatadir, "libltdl", "libltdl"),
                dirs_exist_ok=True)
        loaders = os.path.join(source_ltdl, "loaders")
        if os.path.isdir(loaders):
            shutil.copytree(
                loaders, os.path.join(pkgdatadir, "libltdl", "loaders"),
                dirs_exist_ok=True)
        return pkgdatadir

    def build(self):
        apply_conandata_patches(self)
        source = self.source_folder

        # The git snapshot has no configure script; generate it with the
        # bundled bootstrap (autopoint --force + autoreconf --force --install).
        if str(self.settings.os) == "OHOS":
            libtool_data = self._stage_libtool_data()
            self.run(
                '_lt_pkgdatadir="{}" sh bootstrap'.format(libtool_data),
                cwd=source, env="conanbuild")
        else:
            self.run("sh bootstrap", cwd=source, env="conanbuild")

        if str(self.settings.os) == "OHOS":
            # libtoolize generates libltdl/configure whose AS_TMPDIR uses a
            # restrictive umask (077 locally, 022 in the conan env); on HMDFS
            # the mode it produces leaves the temp dir unwritable by the build
            # process (E052/E060).  Align it with the main configure's
            # AS_TMPDIR override (002) via a regex so any source umask works.
            ltdl_configure = os.path.join(source, "libltdl", "configure")
            if os.path.isfile(ltdl_configure):
                with open(ltdl_configure, "r", encoding="utf-8") as handle:
                    ltdl_cfg = handle.read()
                ltdl_cfg = re.sub(r"umask 0\d\d", "umask 002", ltdl_cfg)
                with open(ltdl_configure, "w", encoding="utf-8") as handle:
                    handle.write(ltdl_cfg)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["scim-1.0"]
        self.cpp_info.includedirs = ["include", "include/scim-1.0"]
        # scim installs CLI tools (scim/scim-config-agent/scim-im-agent) into
        # bin/; declare bindirs so PF8 treats this as a library+tools package.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = ["gtk::gtk", "libltdl::libltdl"]
        self.cpp_info.set_property("pkg_config_name", "scim")
