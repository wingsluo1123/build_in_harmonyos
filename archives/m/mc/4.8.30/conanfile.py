#!/usr/bin/env python3
"""Conan recipe for Midnight Commander (mc) 4.8.30.

Midnight Commander is a visual file manager for Unix-like systems.
Built with S-Lang terminal library and GLib on HarmonyOS.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class McConan(ConanFile):
    name = "mc"
    version = "4.8.30"
    description = "Midnight Commander - visual file manager, Norton Commander style"
    license = "GPL-3.0"
    homepage = "https://www.midnight-commander.org"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib2/2.88.0")
        self.requires("slang/2.3.3")

    def build_requirements(self):
        # automake and libtool available as Conan packages
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Platform-specific configure args
        tc.configure_args.append("--with-slang")
        tc.configure_args.append("--without-x")
        tc.generate()
        # Generate pkg-config files for dependencies
        pc = PkgConfigDeps(self)
        pc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Ensure build tools are in PATH (Harmonybrew install)
        hb_bin = os.path.expanduser("~/.harmonybrew/bin")
        if os.path.isdir(hb_bin):
            env_path = os.environ.get("PATH", "")
            os.environ["PATH"] = hb_bin + ":" + env_path

        # Ensure CC/CXX are set (HarmonyOS doesn't have cc/c++ symlinks by default)
        os.environ.setdefault("CC", "clang")
        os.environ.setdefault("CXX", "clang++")

        # Fix .la files in conan dependencies (libdir path is incorrect)
        self._fix_la_files()

        # Create dummy libtermcap (slang needs termcap symbols, not available on HarmonyOS)
        self._create_dummy_termcap()

        # Add m4_pattern_allow to configure.ac (workaround for autoconf 2.73+
        # treating dnl/AC_MSG_WARN/AC_MSG_ERROR as undefined macros)
        configure_ac = os.path.join(self.source_folder, "configure.ac")
        with open(configure_ac, "r") as f:
            content = f.read()
        allow = (
            "m4_pattern_allow([dnl])\n"
            "m4_pattern_allow([AC_MSG_WARN])\n"
            "m4_pattern_allow([AC_MSG_ERROR])\n"
            "m4_pattern_allow([AM_GNU_GETTEXT])\n"
            "m4_pattern_allow([AM_GNU_GETTEXT_VERSION])\n"
            "m4_ifdef([AM_GNU_GETTEXT], [], [AC_DEFUN([AM_GNU_GETTEXT], [])])\n"
            "m4_ifdef([AM_GNU_GETTEXT_VERSION], [], [AC_DEFUN([AM_GNU_GETTEXT_VERSION], [])])\n"
        )
        if "m4_pattern_allow([dnl])" not in content:
            content = allow + content
            with open(configure_ac, "w") as f:
                f.write(content)

        # Create m4 directory (GitHub archive doesn't include it)
        os.makedirs(os.path.join(self.source_folder, "m4"), exist_ok=True)

        # Create minimal gettext po-files (autopoint is skipped with AUTOPOINT=true)
        self._create_gettext_po_files()

        # Run autoreconf to generate configure script
        # (GitHub archive doesn't include pre-generated configure)
        # Skip autopoint (gettext) since it's not available on CI worker
        os.environ["AUTOPOINT"] = "true"
        aclocal_paths = [
            os.path.join(self.source_folder, "m4"),
            os.path.join(self.source_folder, "m4.include"),
        ]
        # Add system pkg-config m4 path if available
        pkg_m4 = "/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal"
        if os.path.isdir(pkg_m4):
            aclocal_paths.append(pkg_m4)
        aclocal_args = " ".join(f"-I {p}" for p in aclocal_paths if os.path.isdir(p))
        self.run(f"autoreconf --install --force {aclocal_args}",
                 env="conanbuild", cwd=self.source_folder)

        # Patch config.guess for HarmonyOS
        self._patch_config_guess()

        # Patch configure: replace umask 077 with umask 022
        # (HarmonyOS file system doesn't support 700-permission temp dirs)
        configure_path = os.path.join(self.source_folder, "configure")
        with open(configure_path, "r") as f:
            content = f.read()
        content = content.replace("umask 077", "umask 022")
        with open(configure_path, "w") as f:
            f.write(content)

        # Create po/Makefile from po/Makefile.in (gettext version mismatch workaround)
        po_makefile_in = os.path.join(self.source_folder, "po", "Makefile.in")
        po_makefile = os.path.join(self.source_folder, "po", "Makefile")
        if os.path.exists(po_makefile_in) and not os.path.exists(po_makefile):
            with open(po_makefile_in, "r") as f:
                content = f.read()
            if "top_builddir" not in content:
                content = content.replace(
                    "top_srcdir = ..", "top_srcdir = ..\ntop_builddir = .."
                )
            content = content.replace("@POMAKEFILEDEPS@", "")
            content = content.replace("$(top_builddir)/config.status", "../config.status")
            with open(po_makefile, "w") as f:
                f.write(content)

        autotools = Autotools(self)
        autotools.configure()

        # Fix po/Makefile in the BUILD directory after configure
        build_po_makefile = os.path.join(self.build_folder, "po", "Makefile")
        if os.path.exists(build_po_makefile):
            with open(build_po_makefile, "r") as f:
                content = f.read()
            if "top_builddir" not in content:
                content = content.replace(
                    "top_srcdir = ..", "top_srcdir = ..\ntop_builddir = .."
                )
            content = content.replace("@POMAKEFILEDEPS@", "")
            content = content.replace("$(top_builddir)/config.status", "../config.status")
            with open(build_po_makefile, "w") as f:
                f.write(content)
        else:
            # Create a minimal po/Makefile with 'all' target
            build_po_dir = os.path.join(self.build_folder, "po")
            if not os.path.isdir(build_po_dir):
                os.makedirs(build_po_dir, exist_ok=True)
            with open(build_po_makefile, "w") as f:
                f.write("all:\n\t@echo 'Skipping po (NLS not configured)'\n"
                        "install:\n\t@echo 'Skipping po install'\n"
                        "clean:\n\tdistclean:\n\tcheck:\n")

        autotools.make(args=["-j1"])

    def _create_dummy_termcap(self):
        """Create dummy libtermcap.a (slang references termcap symbols)."""
        # Use user-local lib dir which is in conan profile's LDFLAGS
        lib_dir = os.path.expanduser("~/usr/local/lib")
        os.makedirs(lib_dir, exist_ok=True)

        tmp_dir = os.path.join(self.build_folder, "termcap_dummy")
        os.makedirs(tmp_dir, exist_ok=True)
        src = os.path.join(tmp_dir, "termcap_dummy.c")
        obj = os.path.join(tmp_dir, "termcap_dummy.o")
        lib = os.path.join(lib_dir, "libtermcap.a")

        with open(src, "w") as f:
            f.write("""/* Dummy termcap - slang provides its own terminal handling */
void tgoto(void) {}
void tgetent(void) {}
void tgetstr(void) {}
void tputs(void) {}
void tgetflag(void) {}
void tgetnum(void) {}
char *BC = 0;
char *UP = 0;
char PC = 0;
""")

        # Use self.run with conanbuild env to get correct CC/AR/PATH
        self.run(f'$CC -c -fPIC "{src}" -o "{obj}"', env="conanbuild")
        self.run(f'llvm-ar rcs "{lib}" "{obj}"', env="conanbuild")

    def _fix_la_files(self):
        """Delete .la files with incorrect libdir paths to force direct .a/.so linking."""
        conan_cache = os.path.expanduser("~/.conan2/p")
        if not os.path.isdir(conan_cache):
            return
        count = 0
        for root, dirs, files in os.walk(conan_cache):
            for f in files:
                if f.endswith(".la"):
                    la_path = os.path.join(root, f)
                    try:
                        with open(la_path, "r") as fh:
                            content = fh.read()
                        if "libdir='//lib'" in content or "libdir='/lib'" in content:
                            os.unlink(la_path)
                            count += 1
                    except (IOError, OSError):
                        pass
        if count > 0:
            self.output.info(f"Deleted {count} .la files with incorrect libdir")

    def _create_gettext_po_files(self):
        """Create minimal gettext po-files (replaces autopoint)."""
        po_dir = os.path.join(self.source_folder, "po")
        os.makedirs(po_dir, exist_ok=True)

        # Minimal po/Makefile.in.in (needed by config.status)
        makefile_in_in = os.path.join(po_dir, "Makefile.in.in")
        if not os.path.exists(makefile_in_in):
            content = """# Minimal po/Makefile.in.in for mc (autopoint skipped)
PACKAGE = mc
VERSION = 4.8.30
SHELL = /bin/sh
srcdir = @srcdir@
top_srcdir = @top_srcdir@
top_builddir = @top_builddir@
VPATH = @srcdir@
prefix = @prefix@
exec_prefix = @exec_prefix@
datadir = @datadir@
datarootdir = @datarootdir@
localedir = $(datadir)/locale
gettextsrcdir = $(datadir)/gettext/po
INSTALL = @INSTALL@
INSTALL_DATA = @INSTALL_DATA@
MSGFMT = @MSGFMT@
GMSGFMT = @GMSGFMT@
XGETTEXT = @XGETTEXT@
MSGMERGE = @MSGMERGE@
DOMAIN = $(PACKAGE)
COPYRIGHT_HOLDER = Free Software Foundation, Inc.
PACKAGE_BUGREPORT = https://www.midnight-commander.org/wiki/NewTicket
SOURCES = $(srcdir)/*.c
POFILES = @POFILES@
GMOFILES = @GMOFILES@
UPDATEPOFILES = @UPDATEPOFILES@
DUMMYPOFILES = @DUMMYPOFILES@
DISTFILES = Makefile.in.in Makevars $(DOMAIN).pot.in
POTFILES = \\
all: all-@USE_NLS@
all-yes: $(DOMAIN).pot
all-no:
$(DOMAIN).pot: $(POTFILES)
	$(XGETTEXT) --default-domain=$(DOMAIN) --add-comments=TRANSLATORS: $(POTFILES)
install: install-exec
install-exec:
install-data: install-data-@USE_NLS@
install-data-no:
install-data-yes:
clean:
distclean:
mostlyclean:
maintainer-clean:
check:
.PHONY: all install install-exec install-data clean distclean mostlyclean maintainer-clean check
"""
            with open(makefile_in_in, "w") as f:
                f.write(content)

        # Create other required gettext files
        for fname, fcontent in [
            ("Makevars.template", "# Makevars.template\n"),
            ("Rules-quot", "# Rules-quot\n"),
            ("boldquot.sed", ""),
            ("en@boldquot.header", ""),
            ("en@quot.header", ""),
            ("insert-header.sin", ""),
            ("quot.sed", ""),
            ("remove-potcdate.sin", ""),
        ]:
            fpath = os.path.join(po_dir, fname)
            if not os.path.exists(fpath):
                with open(fpath, "w") as f:
                    f.write(fcontent)

    def _patch_config_guess(self):
        """Patch config.guess and config.sub for HarmonyOS support."""
        config_dir = os.path.join(self.source_folder, "config")

        # Patch config.guess
        guess_path = os.path.join(config_dir, "config.guess")
        if os.path.exists(guess_path):
            with open(guess_path, "r") as f:
                content = f.read()
            content = content.replace(
                "Linux|GNU|GNU/*)", "Linux|GNU|GNU/*|HarmonyOS)"
            )
            content = content.replace(
                "    aarch64:Linux:*:*)",
                '    aarch64:HarmonyOS:*:*)\n\tGUESS="$UNAME_MACHINE-unknown-linux-gnu"\n\t;;\n    aarch64:Linux:*:*)',
            )
            with open(guess_path, "w") as f:
                f.write(content)

        # Patch config.sub
        sub_path = os.path.join(config_dir, "config.sub")
        if os.path.exists(sub_path):
            with open(sub_path, "r") as f:
                content = f.read()
            content = content.replace(
                "\t\t\t| linux-* \\",
                "\t\t\t| ohos-* \\\n\t\t\t| linux-* \\",
            )
            with open(sub_path, "w") as f:
                f.write(content)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        # mc is an application, not a library
        self.cpp_info.bindirs = ["bin"]
