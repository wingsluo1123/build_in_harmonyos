#!/usr/bin/env python3
"""Native aarch64 INDI Pentax 1.0 MSC application recipe."""
import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class IndiPentaxConan(ConanFile):
    name = "indi-pentax"
    version = "1.0"
    package_type = "application"
    description = "Pentax INDI MSC camera driver and offline JPEG/RAW to FITS converter"
    license = "LGPL-2.1-or-later", "LGPL-3.0-or-later"
    homepage = "https://github.com/indilib/indi-3rdparty/tree/master/indi-pentax"
    settings = "os", "arch", "compiler", "build_type"
    default_options = {"libindi/*:shared": False, "libev/*:shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libindi/2.2.2.1")
        self.requires("libpktriggercord/0.85.1-20221221181244")
        self.requires("cfitsio/4.6.4")
        self.requires("libraw/0.22.1")
        self.requires("libjpeg/10")
        self.requires("zlib/1.3.1.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS") or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("This recipe implements the upstream aarch64 MSC build")
        if self.dependencies["libindi"].options.shared:
            raise ConanInvalidConfiguration("The driver requires libindi's static archives")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], filename="indi-3rdparty.tar.gz", strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["INDI_PENTAX_USE_CONAN"] = True
        tc.variables["INDI_STATIC_LIBRARY_DIR"] = os.path.join(
            self.dependencies["libindi"].package_folder, "lib").replace("\\", "/")
        # Installing must preserve the linker's OHOS ELF signature.
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        tc.variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = False
        tc.variables["CMAKE_INSTALL_RPATH"] = ""
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="indi-pentax")
        cmake.build()
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "not_applicable", "framework": "none",
            "command": "source audit: indi-pentax/CMakeLists.txt and directory tree",
            "discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
            "reason": "Pinned upstream indi-pentax has no automated test suite"}))

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"),
             excludes=["*/LICENSE"])
        copy(self, "COPYING", os.path.join(self.source_folder, "libpktriggercord", "src"),
             os.path.join(self.package_folder, "licenses", "pktriggercord"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
