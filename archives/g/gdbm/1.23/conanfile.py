#!/usr/bin/env python3
"""Conan recipe for gdbm 1.23 on HarmonyOS PC (aarch64)."""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GdbmConan(ConanFile):
    name = "gdbm"
    version = "1.23"
    description = "GNU database library — a set of database routines that use extensible hashing"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org.ua/software/gdbm/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-libgdbm-compat")
        tc.configure_args.append("--disable-nls")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Fix umask 077 → 022 for HMDFS compatibility (E011)
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 022")
        # Create fake makeinfo to skip documentation build (not available on OHOS)
        makeinfo_path = os.path.join(self.build_folder, "makeinfo")
        with open(makeinfo_path, "w") as f:
            f.write("#!/bin/sh\n"
                    "# Fake makeinfo — create empty .info files\n"
                    "for arg in \"$@\"; do\n"
                    "  case \"$arg\" in\n"
                    "    *.texi)\n"
                    '      base="${arg##*/}"\n'
                    '      base="${base%.texi}"\n'
                    '      touch "$base.info" 2>/dev/null || true\n'
                    "      ;;\n"
                    "    -o)\n"
                    '      out="next"\n'
                    "      ;;\n"
                    "    *)\n"
                    '      if [ "$out" = "next" ]; then\n'
                    '        touch "$arg" 2>/dev/null || true\n'
                    '        out=""\n'
                    "      fi\n"
                    "      ;;\n"
                    "  esac\n"
                    "done\n")
        os.chmod(makeinfo_path, 0o755)
        os.environ["PATH"] = os.path.dirname(makeinfo_path) + ":" + os.environ.get("PATH", "")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gdbm", "gdbm_compat"]
        self.cpp_info.set_property("pkg_config_name", "gdbm")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = []
