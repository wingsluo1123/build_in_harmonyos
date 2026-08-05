import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BrunsliConan(ConanFile):
    name = "brunsli"
    version = "v0.1"
    description = "JPEG Brunsli compression codec (Brotli-based JPEG recompression)"
    license = "Apache-2.0"
    homepage = "https://github.com/google/brunsli"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Download brunsli source
        get(self, **self.conan_data["sources"]["brunsli"], strip_root=True)
        # Remove Bazel BUILD file to avoid conflict with CMake build/ directory
        # on case-insensitive filesystems (HMDFS: BUILD == build)
        if os.path.exists("BUILD"):
            os.remove("BUILD")
        # Download brotli submodule (GitHub tarball doesn't include git submodules)
        get(self, **self.conan_data["sources"]["brotli"], strip_root=True,
            destination="third_party/brotli")
        # Download googletest submodule
        get(self, **self.conan_data["sources"]["googletest"], strip_root=True,
            destination="third_party/googletest")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # cmake_minimum_required(VERSION 3.1) incompatible with cmake 4.x
        # Must pass as -D flag, not toolchain variable (needs to be set
        # before cmake_minimum_required() is processed)
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream install only installs shared libs and headers
        # Copy executables not installed by upstream CMake
        copy(self, "cbrunsli", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "dbrunsli", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        # Copy static libraries not installed by upstream CMake
        copy(self, "*-static.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # Copy brotli headers (needed by brunsli static lib consumers)
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "third_party", "brotli", "c", "include", "brotli"),
             dst=os.path.join(self.package_folder, "include", "brotli"))

    def package_info(self):
        self.cpp_info.libs = [
            "brunslienc-static",
            "brunslidec-static",
            "brunslicommon-static",
            "brotlienc-static",
            "brotlidec-static",
            "brotlicommon-static",
        ]
        self.cpp_info.bindirs = ["bin"]
