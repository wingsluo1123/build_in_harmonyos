#!/usr/bin/env python3
"""Conan recipe for falcosecurity-libs 0.25.4."""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class FalcoSecurityLibsConan(ConanFile):
    name = "falcosecurity-libs"
    version = "0.25.4"
    description = "Core libscap and libsinsp userspace libraries for Falco and Sysdig"
    license = "Apache-2.0"
    homepage = "https://github.com/falcosecurity/libs"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], filename="falcosecurity-libs.tar.gz", strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["FALCOSECURITY_LIBS_VERSION"] = str(self.version)
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "HarmonyOS"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.cache_variables["CMAKE_C_COMPILER_TARGET"] = "aarch64-linux-ohos"
            tc.cache_variables["CMAKE_CXX_COMPILER_TARGET"] = "aarch64-linux-ohos"
            # OHOS Clang defines __linux__; avoid pulling in Linux platform
            # stubs via a project-level macro rather than __OHOS__ guards.
            tc.cache_variables["HAS_LINUX_PLATFORM"] = False
            tc.preprocessor_definitions["HAS_LINUX_PLATFORM"] = "0"
        else:
            tc.cache_variables["HAS_LINUX_PLATFORM"] = True
            tc.preprocessor_definitions["HAS_LINUX_PLATFORM"] = "1"
        tc.cache_variables["USE_BUNDLED_DEPS"] = True
        tc.cache_variables["USE_BUNDLED_DRIVER"] = False
        tc.cache_variables["MUSL_OPTIMIZED_BUILD"] = self.settings.os == "OHOS"
        tc.cache_variables["BUILD_SHARED_LIBS"] = True
        tc.cache_variables["CREATE_TEST_TARGETS"] = False
        tc.cache_variables["ENABLE_E2E_TESTS"] = False
        tc.cache_variables["ENABLE_DRIVERS_TESTS"] = False
        tc.cache_variables["ENABLE_LIBSCAP_TESTS"] = False
        tc.cache_variables["ENABLE_LIBSCAP_FUZZERS"] = False
        tc.cache_variables["ENABLE_LIBSCAP_FUZZ_TOOLS"] = False
        tc.cache_variables["ENABLE_LIBSINSP_E2E_TESTS"] = False
        tc.cache_variables["ENABLE_BENCHMARKS"] = False
        tc.cache_variables["BUILD_LIBSCAP_EXAMPLES"] = False
        tc.cache_variables["BUILD_LIBSINSP_EXAMPLES"] = False
        tc.cache_variables["BUILD_LIBSCAP_MODERN_BPF"] = False
        tc.cache_variables["ENABLE_ENGINE_KMOD"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "falcosecurity-libs")
        self.cpp_info.set_property("cmake_target_name", "falcosecurity-libs::falcosecurity-libs")
        self.cpp_info.includedirs = ["include/falcosecurity"]
        self.cpp_info.libdirs = ["lib", "lib/falcosecurity"]
        self.cpp_info.libs = ["sinsp", "scap", "scap_event_schema"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread"]
