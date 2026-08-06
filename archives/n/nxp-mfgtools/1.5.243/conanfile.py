#!/usr/bin/env python3
"""Conan recipe for nxp-mfgtools (uuu) 1.5.243 — NXP USB firmware deployment tool.

uuu (Universal Update Utility) is NXP's USB firmware programming tool for
i.MX series processors. It builds a single CLI executable using CMake.

Dependencies (all published on ohpcd):
  - bzip2/1.0.8     (bzip2 decompression for firmware images)
  - zlib/1.3.1      (zlib decompression)
  - libusb/1.0.27   (USB device access)
  - zstd/1.5.7      (Zstandard decompression)
  - tinyxml2/11.0.0 (XML config parsing)
  - openssl/3.5.6   (HTTPS download support; also fixes base64_encode scope bug)

OHOS adaptations (patches in conandata.yml):
  - 0001: Replace pkg_check_modules with Conan CMakeDeps find_package targets
    in libuuu/CMakeLists.txt for dependency resolution
  - 0002: Add __OHOS__ guard for stat64→stat in buffer.cpp (OHOS musl libc
    lacks stat64)
  - 0003: Add __OHOS__ guard for mmap64→mmap in buffer.h (OHOS musl libc
    lacks mmap64)
  - 0004: Replace pkg_check_modules with Conan CMakeDeps find_package targets
    in uuu/CMakeLists.txt, add find_package(bzip2)
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class NxpmfgtoolsConan(ConanFile):
    name = "nxp-mfgtools"
    version = "1.5.243"
    description = "NXP Universal Update Utility (uuu) — USB firmware deployment tool"
    license = "BSD-3-Clause"
    homepage = "https://github.com/nxp-imx/mfgtools"
    url = ""  # CI fills this

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("bzip2/1.0.8")
        self.requires("zlib/1.3.1")
        self.requires("libusb/1.0.27")
        self.requires("zstd/1.5.7")
        self.requires("tinyxml2/11.0.0")
        self.requires("openssl/3.5.6")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"nxp-mfgtools is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Create .tarball-version so gen_ver.sh doesn't fail without git
        with open(self.source_folder + "/.tarball-version", "w") as f:
            f.write("1.5.243")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "nxp-mfgtools")
        self.cpp_info.set_property("cmake_target_name", "nxp-mfgtools::nxp-mfgtools")
        # The executable is installed to bin/
        self.cpp_info.bindirs = ["bin"]
