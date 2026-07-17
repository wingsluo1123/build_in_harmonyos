#!/usr/bin/env python3
"""Conan recipe for the gtk-mac-integration 3.0.2 compatibility API."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps


class GtkMacIntegrationConan(ConanFile):
    name = "gtk-mac-integration"
    version = "3.0.2"
    description = "Portable compatibility layer for the gtk-mac-integration API"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gtk-mac-integration"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "the compatibility backend supports Linux and OHOS"
            )

    def requirements(self):
        self.requires("glib/2.84.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "*",
            src=os.path.join(self.recipe_folder, "ohos"),
            dst=os.path.join(self.export_sources_folder, "ohos"),
        )

    def layout(self):
        cmake_layout(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.fPIC
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "ohos"))
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["gtkmacintegration-gtk3"]
        self.cpp_info.set_property("cmake_file_name", "gtk-mac-integration")
        self.cpp_info.set_property(
            "cmake_target_name", "gtk-mac-integration::gtk-mac-integration"
        )
        self.cpp_info.set_property("pkg_config_name", "gtk-mac-integration-gtk3")
        self.cpp_info.defines = ["GTKOSX_HARMONYOS_COMPAT=1"]
