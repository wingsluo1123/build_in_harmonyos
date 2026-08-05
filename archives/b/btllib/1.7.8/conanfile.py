#!/usr/bin/env python3
"""Conan recipe for btllib 1.7.8 — Birol Lab Library (bioinformatics C++ toolkit).

Build system: Meson with CMake subprojects (cpptoml, sdsl-lite, argparse).
OpenMP: provided by system clang (no conan dependency needed).
Subproject CMake version fixes are applied via sed in source() since
the submodules are cloned dynamically and not tracked by refresh-patch.
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.cmake import cmake_layout


class BtllibConan(ConanFile):
    name = "btllib"
    version = "1.7.8"
    description = "Birol Lab Library - bioinformatics C++ toolkit"
    license = "GPL-3.0"
    homepage = "https://github.com/BirolLab/btllib"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Download main source tarball
        get(self, **self.conan_data["sources"], strip_root=True)

        # Workaround: git dubious ownership in conan cache
        self.run("git config --global --add safe.directory '*'")

        # Clone git submodules at the exact commits pinned by btllib v1.7.8
        subprojects_dir = os.path.join(self.source_folder, "subprojects")
        submodules = [
            ("cpptoml", "https://github.com/skystrife/cpptoml.git",
             "fededad7169e538ca47e11a9ee9251bc361a9a65"),
            ("sdsl-lite", "https://github.com/simongog/sdsl-lite.git",
             "c32874cb2d8524119f25f3b501526fe692df29f4"),
            ("argparse", "https://github.com/p-ranav/argparse.git",
             "15d745f58481158ceb65f860e379deac9f722b5d"),
        ]
        for name, url, commit in submodules:
            target = os.path.join(subprojects_dir, name)
            self.run(f"git clone {url} {target}")
            self.run(f"cd {target} && git checkout {commit}")

        # Nested submodules
        # cpptoml/deps/meta-cmake
        meta_cmake = os.path.join(subprojects_dir, "cpptoml", "deps", "meta-cmake")
        os.makedirs(os.path.dirname(meta_cmake), exist_ok=True)
        self.run(f"git clone https://github.com/meta-toolkit/meta-cmake.git {meta_cmake}")
        self.run(f"cd {meta_cmake} && git checkout db7ff976c430a6cb6cbd03ae691be04cfaac0a07")

        # sdsl-lite/external/googletest
        gtest = os.path.join(subprojects_dir, "sdsl-lite", "external", "googletest")
        os.makedirs(os.path.dirname(gtest), exist_ok=True)
        self.run(f"git clone https://github.com/google/googletest.git {gtest}")
        self.run(f"cd {gtest} && git checkout c2d90bddc6a2a562ee7750c14351e9ca16a6a37a")

        # sdsl-lite/external/libdivsufsort
        libdivsufsort = os.path.join(subprojects_dir, "sdsl-lite", "external", "libdivsufsort")
        os.makedirs(os.path.dirname(libdivsufsort), exist_ok=True)
        self.run(f"git clone https://github.com/simongog/libdivsufsort.git {libdivsufsort}")
        self.run(f"cd {libdivsufsort} && git checkout 0f24acd8de208464769c782119dacf158647f7ed")

        # Fix CMake minimum version for CMake 4.x compatibility in all subprojects
        cmake_files = [
            "subprojects/cpptoml/CMakeLists.txt",
            "subprojects/sdsl-lite/CMakeLists.txt",
            "subprojects/sdsl-lite/external/googletest/googletest/CMakeLists.txt",
            "subprojects/sdsl-lite/external/libdivsufsort/CMakeLists.txt",
        ]
        for cmake_file in cmake_files:
            full_path = os.path.join(self.source_folder, cmake_file)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    content = f.read()
                # Replace any cmake_minimum_required(VERSION X.Y.Z) with 3.5...4.1
                content = re.sub(
                    r'cmake_minimum_required\s*\(\s*VERSION\s+[\d.]+\s*\)',
                    'cmake_minimum_required(VERSION 3.5...4.1)',
                    content
                )
                with open(full_path, 'w') as f:
                    f.write(content)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["b_coverage"] = "false"
        tc.project_options["werror"] = "false"
        if self.settings.os in ("Linux", "OHOS"):
            tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["btllib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "m", "pthread", "omp"]
