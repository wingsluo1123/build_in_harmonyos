#!/usr/bin/env python3
"""Conan recipe for scim-thai 0.1.4 (SCIM Thai IMEngine module).

The upstream git snapshot omits generated Autotools files; the recipe runs
the bundled autogen.sh (libtoolize + autopoint + aclocal + autoheader +
automake + autoconf) first.

Source patches applied:
  1. configure.ac -- override AS_TMPDIR so config.status uses umask 002.
     HMDFS maps directory owners to a fixed uid; 0700 temp dirs created with
     umask 077 are not writable by the build process (E052/E060).

Exported sources beside the recipe:
  - m4/pkg.m4 -- the upstream snapshot lacks pkg.m4; without it the
     PKG_CHECK_MODULES macro stays unexpanded and configure fails.  The
     gettext macro chain and config.rpath are produced by autopoint during
     autogen.sh (see below).

Conan gettext autopoint quirk: the packaged autopoint script bakes
prefix="/" (relocation artifact), so it resolves gettext_datadir to
//share/gettext, cannot find its own share/gettext/archive.dir.tar.xz, and
dies with "infrastructure files for version X not found" -- leaving
po/Makefile.in.in absent and configure failing.  The recipe emits a relocated
autopoint (prefix = gettext package folder) and prepends it on PATH.

Dependency quirk (scim consumer): the released scim package's
libscim-1.0.la embeds a broken absolute dependency '//lib/libltdl.la'
(prefix=/ relocation artifact).  Libtool then fails with "'//lib/libltdl.la'
is not a valid libtool archive" when linking thai.la.  The recipe patches
that .la inside the scim dependency package before linking (removes only the
invalid reference; -lltdl -L<libltdl dir> are already present).
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class ScimThaiConan(ConanFile):
    name = "scim-thai"
    version = "0.1.4"
    description = "Thai input method engine (IMEngine) module for SCIM"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/tlwg/scim-thai"
    url = "https://github.com/tlwg/scim-thai"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    package_type = "library"

    def export_sources(self):
        export_conandata_patches(self)
        # The upstream git snapshot omits pkg.m4 (PKG_CHECK_MODULES); ship it
        # beside the recipe so aclocal can expand the macro (scim pattern).
        # The gettext macro chain and config.rpath come from the relocated
        # autopoint run in build().
        macro_dir = os.path.join(self.recipe_folder, "m4")
        if os.path.isdir(macro_dir):
            shutil.copytree(
                macro_dir,
                os.path.join(self.export_sources_folder, "m4"),
                dirs_exist_ok=True,
            )

    def requirements(self):
        # PKG_CHECK_MODULES(SCIM, scim >= 0.99.8) + scim-gtkutils (optional,
        # detected no on OHOS), PKG_CHECK_MODULES(LIBTHAI, libthai).
        self.requires("scim/1.4.18-git20211204")
        self.requires("libthai/0.1.29")

    def build_requirements(self):
        # The git snapshot has no configure; autogen.sh needs the full stack.
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        # gettext/0.22.5.1 provides autopoint + msgmerge/msgfmt/xgettext bin
        # tools (0.22.5 shipped only libintl without them).
        self.tool_requires("gettext/0.22.5.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = PkgConfigDeps(self)
        deps.generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        # scim-thai builds a dlopen-able SCIM IMEngine module (thai.so
        # installed into $(SCIM_MODULEDIR)/IMEngine); it MUST be a shared
        # module — the SCIM framework loads IMEngine plugins at runtime, a
        # static archive is useless here.  So force shared and disable the
        # static archive regardless of the generic 'shared' option.
        tc.configure_args.extend([
            "--enable-shared",
            "--disable-static",
        ])
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
            # HNP clang is libc++ built; its libc++.so lives in the OHOS SDK
            # <llvm>/lib/aarch64-linux-ohos which the profile does not add to
            # LD_LIBRARY_PATH (same fix as the scim recipe).
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
            # aclocal/automake/autopoint are perl scripts; the conan perl
            # package injects PERL5LIB pointing at its own XS modules which the
            # system perl interpreter cannot dlopen (Perl_my_cxt_init symbol
            # not found).  Pin PERL to the HNP perl and restrict PERL5LIB to the
            # automake package's pure-perl module dir (scim pattern).
            system_perl = os.path.join(tool_dir, "perl")
            if os.path.exists(system_perl):
                env.define_path("PERL", system_perl)
            automake = self.dependencies.build["automake"]
            automake_share = os.path.join(
                automake.package_folder, "share", "automake-1.18")
            env.define_path("PERL5LIB", automake_share)
            env.vars(self).save_script("scim_thai_env")

    def _fix_scim_la(self):
        """Remove the invalid '//lib/libltdl.la' reference embedded in the
        released scim package's libscim-1.0.la dependency_libs so libtool can
        link thai.la (-lltdl + -L are already listed next to it)."""
        scim = self.dependencies["scim"]
        la_path = os.path.join(scim.package_folder, "lib", "libscim-1.0.la")
        if not os.path.isfile(la_path):
            return
        with open(la_path, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        fixed = content.replace(" //lib/libltdl.la", "")
        if fixed != content:
            with open(la_path, "w", encoding="utf-8") as handle:
                handle.write(fixed)

    def _relocate_autopoint(self):
        """conan gettext's autopoint bakes prefix="/" (relocation artifact), so
        gettext_datadir becomes //share/gettext and autopoint cannot find the
        package's own share/gettext/archive.dir.tar.xz ("infrastructure files
        for version X not found"), leaving po/Makefile.in.in missing.  Emit a
        copy whose prefix points at the gettext package folder; the caller
        prepends its directory on PATH."""
        gettext = self.dependencies.build["gettext"]
        src = os.path.join(gettext.package_folder, "bin", "autopoint")
        if not os.path.isfile(src):
            return None
        fix_dir = os.path.join(self.build_folder, "gettext-autopoint-fix")
        os.makedirs(fix_dir, exist_ok=True)
        dst = os.path.join(fix_dir, "autopoint")
        with open(src, "r", encoding="utf-8", errors="replace") as handle:
            script = handle.read()
        script = script.replace(
            'prefix="/"', 'prefix="' + gettext.package_folder + '"', 1)
        with open(dst, "w", encoding="utf-8") as handle:
            handle.write(script)
        os.chmod(dst, 0o755)
        return fix_dir

    def build(self):
        apply_conandata_patches(self)
        self._fix_scim_la()
        source = self.source_folder

        # The git snapshot has no configure; generate it with autogen.sh.
        # Prepend the relocated autopoint (see _relocate_autopoint) so the
        # hermetic CI environment does not use the broken packaged one.
        fix_dir = self._relocate_autopoint()
        prefix = 'export PATH="{}:$PATH"; '.format(fix_dir) if fix_dir else ''
        self.run(prefix + "sh autogen.sh", cwd=source, env="conanbuild")

        if str(self.settings.os) == "OHOS":
            # libtoolize may generate in-tree libtool fragments whose
            # AS_TMPDIR uses a restrictive umask (077); on HMDFS the temp dir
            # becomes unwritable by the build process (E052/E060).  Align any
            # generated configure with the main AS_TMPDIR override (002).
            for candidate in ("libltdl/configure", "configure"):
                path = os.path.join(source, candidate)
                if os.path.isfile(path):
                    with open(path, "r", encoding="utf-8") as handle:
                        text = handle.read()
                    fixed = re.sub(r"umask 0\d\d", "umask 002", text)
                    if fixed != text:
                        with open(path, "w", encoding="utf-8") as handle:
                            handle.write(fixed)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # HMDFS ginstall truncates the ~2.3MB thai.so during install
        # ("error deallocating ... Permission denied", corrupt ELF, dlopen
        # fails with Permission denied).  Re-copy the complete libtool
        # artifact from the build tree with conan's reliable copy().
        so_dir = os.path.join(self.build_folder, "src", ".libs")
        if os.path.isdir(so_dir):
            copy(
                self,
                "thai.so",
                src=so_dir,
                dst=os.path.join(
                    self.package_folder, "lib", "scim-1.0", "IMEngine"))

    def package_info(self):
        # scim-thai installs a SCIM IMEngine module (thai.so) into the scim
        # module dir; consumers load it at runtime through the SCIM framework,
        # so no conventional -l library is exposed.  libs is declared empty
        # explicitly to make that intent unambiguous.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
