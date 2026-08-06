#!/usr/bin/env python3
"""Test package for json-glib — uses PkgConfigDeps + CMakeToolchain.
Copies and fixes .pc files from json-glib and glib2 packages (which have
meson-generated .pc files with Requires chains but broken prefix=/).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class JsonglibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # The meson-generated .pc files in json-glib and glib2 packages have
        # Requires chains (json-glib-1.0 → gio-2.0 → glib-2.0 → pcre2, etc.)
        # but prefix=/ is broken. Copy them to the generators folder with the
        # correct prefix, overwriting the PkgConfigDeps-generated versions.
        for dep_name in ("json-glib", "glib2"):
            dep = self.dependencies.get(dep_name)
            if dep is None:
                continue
            dep_prefix = dep.package_folder
            pc_src_dir = os.path.join(dep_prefix, "lib", "pkgconfig")
            if not os.path.isdir(pc_src_dir):
                continue
            for pc_file in os.listdir(pc_src_dir):
                if not pc_file.endswith(".pc"):
                    continue
                src_path = os.path.join(pc_src_dir, pc_file)
                with open(src_path) as f:
                    content = f.read()
                content = content.replace("prefix=/", f"prefix={dep_prefix}")
                dst_path = os.path.join(self.generators_folder, pc_file)
                with open(dst_path, "w") as f:
                    f.write(content)
        os.environ["PKG_CONFIG_PATH"] = (
            self.generators_folder + os.pathsep
            + os.environ.get("PKG_CONFIG_PATH", "")
        )

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the test binary directly (CI L0d requires self.run() in test())
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_json_glib"), env="conanrun")
