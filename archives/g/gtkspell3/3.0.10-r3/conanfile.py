#!/usr/bin/env python3
"""Conan recipe — gtkspell3 3.0.10-r3 (GTK spell-check library, autotools).

OHOS notes:
- Pre-generated configure; --host/--build for aarch64-unknown-linux-ohos.
- intltool is not packaged on CI workers; provide configure-time stubs +
  a minimal XML::Parser so IT_PROG_INTLTOOL / XML::Parser probes pass.
- Build only the gtkspell/ subdir (skip examples/po/docs) to avoid msgfmt
  and demo link failures when optional tooling is missing.
- System deps (gtk+-3.0, enchant-2, glib-2.0) expected under DEFAULT_PREFIX.
- Sign installed .so for XPM dlopen.
"""
import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Gtkspell3Conan(ConanFile):
    name = "gtkspell3"
    version = "3.0.10-r3"
    description = "GtkSpell3 — spell-checking for GTK+ text widgets"
    license = "LGPL-2.1-or-later"
    homepage = "https://gtkspell.sourceforge.net/"
    url = ""
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # pure C library
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        basic_layout(self, src_folder=".")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS", "Macos"):
            raise ConanInvalidConfiguration(
                f"{self.ref} supports Linux/OHOS (got {self.settings.os})"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        # library only; demos/docs/introspection not needed for package
        tc.configure_args.append("--disable-gtk-doc")
        tc.configure_args.append("--enable-introspection=no")
        tc.configure_args.append("--enable-vala=no")
        tc.configure_args.append("--disable-iso-codes")
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--enable-gtk3")
        tc.configure_args.append("--disable-gtk2")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        # Prefer system/usr/local pkg-config data (gtk3/enchant/glib)
        prefix = os.environ.get(
            "DEFAULT_PREFIX", "/storage/Users/currentUser/usr/local"
        )
        pc = os.path.join(prefix, "lib", "pkgconfig")
        existing = os.environ.get("PKG_CONFIG_PATH", "")
        if existing:
            tc.configure_args.append(f"PKG_CONFIG_PATH={pc}:{existing}")
        else:
            tc.configure_args.append(f"PKG_CONFIG_PATH={pc}")
        tc.generate()

    def _prepare_intltool_stubs(self):
        """CI has no intltool; configure still runs IT_PROG_INTLTOOL + XML::Parser."""
        stub_dir = os.path.join(self.build_folder, "ohos-bin")
        perl_lib = os.path.join(self.build_folder, "ohos-perl")
        os.makedirs(stub_dir, exist_ok=True)
        os.makedirs(os.path.join(perl_lib, "XML"), exist_ok=True)

        stub = textwrap.dedent(
            """\
            #!/bin/sh
            # OHOS CI stub — satisfy intltool version probe; no real NLS merge.
            if [ "$1" = "--version" ] || [ "$1" = "-V" ]; then
                echo "intltool 0.51.0"
                exit 0
            fi
            exit 0
            """
        )
        for name in ("intltool-update", "intltool-merge", "intltool-extract"):
            path = os.path.join(stub_dir, name)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(stub)
            os.chmod(path, 0o755)

        parser_pm = os.path.join(perl_lib, "XML", "Parser.pm")
        with open(parser_pm, "w", encoding="utf-8") as fh:
            fh.write("package XML::Parser;\n1;\n")

        path = stub_dir + os.pathsep + os.environ.get("PATH", "")
        os.environ["PATH"] = path
        perl5 = perl_lib + os.pathsep + os.environ.get("PERL5LIB", "")
        os.environ["PERL5LIB"] = perl5
        self.output.info(f"intltool stubs on PATH: {stub_dir}")

    def _patch_configure_hmdfs(self):
        """HMDFS: umask 077 + relative mktemp → Permission denied on config.status."""
        cfg = os.path.join(self.source_folder, "configure")
        self.run(
            "sed -i"
            " -e 's/umask 077/umask 022/g'"
            r" -e 's|mktemp -d \"\./confXXXXXX\"|mktemp -d \"${TMPDIR:-/tmp}/confXXXXXX\"|g'"
            " configure",
            cwd=self.source_folder,
        )
        if not os.path.isfile(cfg):
            raise ConanInvalidConfiguration("configure missing after source()")

    def build(self):
        # Ensure temp dirs are creatable on HMDFS before any configure helper runs.
        try:
            os.umask(0o022)
        except Exception:
            pass
        self._prepare_intltool_stubs()
        self._patch_configure_hmdfs()

        autotools = Autotools(self)
        autotools.configure()

        # Only build the library; skip examples / po / docs.
        makefile = os.path.join(self.build_folder, "Makefile")
        if os.path.isfile(makefile):
            self.run(
                "sed -i 's/^SUBDIRS = .*/SUBDIRS = gtkspell/' Makefile",
                cwd=self.build_folder,
            )
        # -j1: OHOS jobserver/mkfifo issues
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as fh:
                return fh.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        """XPM requires signed .so for dlopen; strip stale .codesign then self-sign."""
        import glob

        targets = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True
        )
        targets += glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True
        )
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for fpath in targets:
            if os.path.islink(fpath):
                continue
            if not self._is_elf(fpath):
                continue
            self.run(
                f'{objcopy} --remove-section .codesign "{fpath}" 2>/dev/null || true'
            )
            self.run(
                f'{signer} sign -inFile "{fpath}" -outFile "{fpath}" -selfSign 1'
            )

    def package_info(self):
        self.cpp_info.libs = ["gtkspell3-3"]
        self.cpp_info.set_property("pkg_config_name", "gtkspell3-3.0")
