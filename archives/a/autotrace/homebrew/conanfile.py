#!/usr/bin/env python3
"""Conan recipe for autotrace homebrew (upstream 0.31.10)."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AutotraceConan(ConanFile):
    name = "autotrace"
    version = "homebrew"
    description = "Bitmap to vector graphics converter and library"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/autotrace/autotrace"
    url = ""
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        prefix = os.environ.get("DEFAULT_PREFIX", os.path.join(os.path.expanduser("~"), "usr", "local"))
        pkg_paths = [os.path.join(prefix, "lib", "pkgconfig")]
        existing = os.environ.get("PKG_CONFIG_PATH")
        if existing:
            pkg_paths.append(existing)
        os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(pkg_paths)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--without-magick",
            "--without-pstoedit",
            "--without-png",
        ])
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        configure_ac = os.path.join(self.source_folder, "configure.ac")
        makefile_am = os.path.join(self.source_folder, "Makefile.am")
        for macro in (
            "IT_PROG_INTLTOOL([0.50.1])",
            "AM_GNU_GETTEXT_VERSION([0.19.3])",
            "AM_GNU_GETTEXT([external])",
            "ALL_LINGUAS=\"ja de\"",
            "AM_GLIB_GNU_GETTEXT",
        ):
            replace_in_file(self, configure_ac, macro, "")
        replace_in_file(
            self,
            configure_ac,
            "AC_CONFIG_FILES([po/Makefile.in Makefile autotrace.pc])",
            "AC_CONFIG_FILES([Makefile autotrace.pc])",
        )
        replace_in_file(self, makefile_am, "SUBDIRS = po", "SUBDIRS =")
        replace_in_file(self, makefile_am, "$(INTLLIBS)", "")
        self.run("autoreconf --force --install --verbose", cwd=self.source_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["autotrace"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = []
        self.cpp_info.set_property("pkg_config_name", "autotrace")
