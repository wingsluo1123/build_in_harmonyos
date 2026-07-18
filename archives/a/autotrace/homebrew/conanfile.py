#!/usr/bin/env python3
"""Conan recipe for autotrace homebrew (upstream 0.31.10)."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
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
        self.run("chmod +x autogen.sh && ./autogen.sh", cwd=self.source_folder)
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
        self.cpp_info.system_libs = ["intl"]
        self.cpp_info.set_property("pkg_config_name", "autotrace")
