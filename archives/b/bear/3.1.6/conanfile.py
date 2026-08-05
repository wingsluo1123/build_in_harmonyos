#!/usr/bin/env python3
"""Conan recipe for Bear 3.1.6 — CMake superbuild.

Bear uses a CMake superbuild (ExternalProject_Add) to download and build
all dependencies (gRPC, protobuf, abseil, boringssl, fmt, spdlog,
nlohmann_json) from source. This recipe wraps the superbuild.

Key adaptations for HarmonyOS:
- gRPC submodules fetched via fetch_submodules.sh (tarball download, not git)
- boringssl patched for HarmonyOS processor detection + UNIX check
- source uses find_package(gRPC CONFIG) instead of pkg_check_modules
- OPENSSL_NO_ASM=ON to avoid missing assembly symbols
- CMAKE_POLICY_VERSION_MINIMUM=3.5 for c-ares compatibility
- Conan toolchain CMAKE_PREFIX_PATH removed to avoid interfering with
  the superbuild's ExternalProject dependency management
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BearConan(ConanFile):
    name = "bear"
    version = "3.1.6"
    description = "Build EAR — generates compilation database for clang tooling"
    license = "GPL-3.0"
    homepage = "https://github.com/rizsotto/Bear"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "fetch_submodules.sh", "patch_boringssl.py"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_UNIT_TESTS"] = False
        tc.variables["ENABLE_FUNC_TESTS"] = False
        tc.generate()

        # Remove CMAKE_PREFIX_PATH from Conan toolchain to prevent it from
        # overriding the superbuild's ExternalProject CMAKE_PREFIX_PATH.
        # The bear CMakeLists.txt manages CMAKE_PREFIX_PATH for its bundled deps.
        tc_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.exists(tc_file):
            with open(tc_file, "r") as f:
                content = f.read()
            lines = content.split("\n")
            filtered = [l for l in lines if "CMAKE_PREFIX_PATH" not in l]
            with open(tc_file, "w") as f:
                f.write("\n".join(filtered))

    def build(self):
        apply_conandata_patches(self)
        # Copy helper scripts to the correct location in the source tree
        grpc_dir = os.path.join(self.source_folder, "third_party", "grpc")
        if os.path.isdir(grpc_dir):
            for script in ("fetch_submodules.sh", "patch_boringssl.py"):
                src = os.path.join(self.source_folder, script)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(grpc_dir, script))
                    if script == "fetch_submodules.sh":
                        os.chmod(os.path.join(grpc_dir, script), 0o755)
        # Set SSL certificate path for HarmonyOS (CA certs installed by init-build)
        cert_path = os.path.join(os.path.expanduser("~"), "usr", "local", "ssl", "cert.pem")
        if os.path.exists(cert_path):
            os.environ["SSL_CERT_FILE"] = cert_path
            os.environ["CURL_CA_BUNDLE"] = cert_path
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
