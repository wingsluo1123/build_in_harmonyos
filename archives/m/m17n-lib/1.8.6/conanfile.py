#!/usr/bin/env python3
"""Conan recipe — m17n-lib 1.8.6

m17n-lib is a multilingual text processing library providing input methods,
character encoding conversion, text layout, and font management.

Homepage: https://www.nongnu.org/m17n/
License: LGPL-2.1
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class M17nLibConan(ConanFile):
    name = "m17n-lib"
    version = "1.8.6"
    description = "Multilingual text processing library for input, output, and display"
    license = "LGPL-2.1"
    homepage = "https://www.nongnu.org/m17n/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libxml2/2.15.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-included-gettext")
        tc.configure_args.append("--without-x")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._generate_plural_h()
        autotools = Autotools(self)
        autotools.configure()
        self._fix_generated_makefile()
        autotools.make(args=["-j1"])

    def _fix_generated_makefile(self):
        """Fix generated src/Makefile to add libintl.a static linking.

        Patch 0008 modifies Makefile.in, but configure may regenerate
        Makefile with different LIBADD. This ensures libintl.a is linked.
        """
        import re
        makefile = os.path.join(self.build_folder, "src", "Makefile")
        if not os.path.exists(makefile):
            return
        with open(makefile, "r") as f:
            content = f.read()
        changed = False
        if "intl/libintl.a" not in content:
            # Add libintl.a to DEPENDENCIES
            content = re.sub(
                r'^(libm17n_core_la_DEPENDENCIES\s*=\s*)$',
                r'\1$(top_builddir)/intl/libintl.a',
                content, flags=re.MULTILINE
            )
            # Add libintl.a to LIBADD
            content = re.sub(
                r'^(libm17n_core_la_LIBADD\s*=\s*.*?)(\s*$)',
                r'\1 $(top_builddir)/intl/libintl.a\2',
                content, flags=re.MULTILINE
            )
            changed = True
        if changed:
            with open(makefile, "w") as f:
                f.write(content)
            self.output.info("Fixed generated Makefile: added libintl.a linking")

    def _generate_plural_h(self):
        """Generate plural.h from plural.y using bison, then fix signature.

        Bison 3.8.2 generates int yyparse(void) but the patched plural.c
        (patch 0005) expects int yyparse(void *arg). This fixes the header.
        """
        intl_dir = os.path.join(self.source_folder, "intl")
        plural_h = os.path.join(intl_dir, "plural.h")
        plural_y = os.path.join(intl_dir, "plural.y")

        if not os.path.exists(plural_h) and os.path.exists(plural_y):
            self.output.info("Generating plural.h from plural.y using bison...")
            try:
                subprocess.run(
                    ["bison", "-d", plural_y, "--header=plural.h"],
                    cwd=intl_dir, check=True,
                    capture_output=True, text=True,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                try:
                    subprocess.run(
                        ["bison", "-d", "-o", "plural.c", plural_y],
                        cwd=intl_dir, check=True,
                        capture_output=True, text=True,
                    )
                except (subprocess.CalledProcessError, FileNotFoundError):
                    self.output.warning("bison not available, plural.h may be missing")

        if os.path.exists(plural_h):
            with open(plural_h, "r") as f:
                content = f.read()
            if "int yyparse (void);" in content:
                content = content.replace(
                    "int yyparse (void);",
                    "int yyparse (void *arg);"
                )
                with open(plural_h, "w") as f:
                    f.write(content)
                self.output.info("Fixed yyparse signature in plural.h")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["m17n-gui", "m17n", "m17n-flt", "m17n-core"]
