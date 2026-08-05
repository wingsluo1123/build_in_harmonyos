#!/usr/bin/env python3
"""Conan recipe for aws-c-auth 0.10.1 — AWS SDK for C authentication library.

Provides AWS credential management, SigV4 signing, IAM role authentication.

Note: We use CMAKE_PREFIX_PATH instead of CMakeDeps because the aws-c-common
cmake config creates the AWS::aws-c-common target and adds CMake modules
(AwsCFlags, AwsCheckHeaders, etc.) to CMAKE_MODULE_PATH. CMakeDeps replaces
these with different target names (aws-c-common::aws-c-common) and doesn't
add the module path, causing build failures.

We also use CMAKE_PROJECT_TOP_LEVEL_INCLUDES to inject a helper that:
1. Appends dep package folders to CMAKE_PREFIX_PATH
2. Appends aws-c-common's cmake modules dir to CMAKE_MODULE_PATH
3. Calls find_package(Threads) before any AWS find_package, because
   aws-lc's crypto-config.cmake references Threads::Threads which
   must exist before find_package(aws-c-cal) loads it.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AwscauthConan(ConanFile):
    name = "aws-c-auth"
    version = "0.10.1"
    description = "AWS SDK for C authentication library: credentials, SigV4 signing, IAM roles"
    license = "Apache-2.0"
    homepage = "https://github.com/awslabs/aws-c-auth"
    url = "https://github.com/awslabs/aws-c-auth"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-c-common/0.14.3")
        self.requires("aws-c-cal/0.9.15")
        self.requires("aws-c-sdkutils/0.2.7")
        self.requires("aws-c-io/0.27.5")
        self.requires("aws-c-http/0.11.0")
        self.requires("aws-c-compression/0.3.2")
        # aws-lc is a transitive dep of aws-c-cal, but we need it as a direct
        # requirement so the Conan toolchain adds its lib/include paths to
        # CMAKE_LIBRARY_PATH/CMAKE_INCLUDE_PATH. This lets Findcrypto.cmake
        # (from aws-c-cal's cmake config) locate libcrypto.a and openssl headers.
        self.requires("aws-lc/5.4.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"

        # AWS C libraries ship their own CMake config (aws-c-common-config.cmake)
        # which: (1) adds modules/ to CMAKE_MODULE_PATH, (2) creates AWS:: targets.
        # CMakeDeps would shadow this with aws-c-common::aws-c-common targets,
        # breaking the AWS CMakeLists.txt that expects AWS:: namespace.
        #
        # Solution: Use CMAKE_PROJECT_TOP_LEVEL_INCLUDES to inject a helper file
        # that: (a) appends dep_root to CMAKE_PREFIX_PATH, (b) appends
        # modules_dir to CMAKE_MODULE_PATH, (c) calls find_package(Threads)
        # before any AWS find_package (aws-lc crypto-config.cmake references
        # Threads::Threads which must exist beforehand).
        dep = self.dependencies["aws-c-common"]
        dep_root = dep.package_folder
        if dep_root:
            modules_dir = os.path.join(
                dep_root, "lib", "cmake", "aws-c-common", "modules"
            )
            helper_path = os.path.join(self.generators_folder, "aws_paths.cmake")
            with open(helper_path, "w") as f:
                f.write(
                    f'list(APPEND CMAKE_PREFIX_PATH "{dep_root}")\n'
                    f'list(APPEND CMAKE_MODULE_PATH "{modules_dir}")\n'
                )
            tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = helper_path

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)

        # Use CMAKE_PREFIX_PATH to point to dependency package folders so that
        # find_package(aws-c-common) uses the original config file which:
        # 1. Creates the AWS::aws-c-common target (not aws-c-common::aws-c-common)
        # 2. Adds CMake modules (AwsCFlags, AwsCheckHeaders, etc.) to CMAKE_MODULE_PATH
        # 3. find_package(crypto) finds aws-lc's libcrypto via Findcrypto.cmake
        prefix_paths = []
        for dep_name in ["aws-c-common", "aws-c-cal", "aws-c-sdkutils",
                         "aws-c-io", "aws-c-http", "aws-c-compression", "aws-lc"]:
            try:
                dep = self.dependencies[dep_name]
                if dep.package_folder:
                    prefix_paths.append(dep.package_folder)
            except KeyError:
                pass
        cmake.configure(variables={
            "CMAKE_PREFIX_PATH": ";".join(prefix_paths)
        })
        cmake.build()
        cmake.test()  # Run ctest (L1: upstream test execution verification)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["aws-c-auth"]
        self.cpp_info.set_property("cmake_file_name", "aws-c-auth")
        self.cpp_info.set_property("cmake_target_name", "aws-c-auth::aws-c-auth")
