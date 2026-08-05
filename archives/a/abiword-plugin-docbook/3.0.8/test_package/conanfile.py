#!/usr/bin/env python3
"""Conan test_package — abiword-plugin-docbook 3.0.8

L1 test: build test.c (dlopen + ABI symbol checks) against the installed
docbook plugin .so and run it. Uses self.run() so the CI L0d gate sees a
real command execution, not a stub.
"""
import os
import glob

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain


class AbiwordPluginDocbookTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["abiword-plugin-docbook"].package_folder
        plugin_dir = os.path.join(pkg_folder, "lib", "abiword", "plugins")

        # Find the docbook plugin .so — keep full path to avoid basename/join mismatch
        docbook_so = []
        if os.path.isdir(plugin_dir):
            docbook_so = [os.path.join(plugin_dir, p) for p in os.listdir(plugin_dir)
                          if "docbook" in p.lower() and p.endswith(".so")]

        if not docbook_so:
            # Fallback: search anywhere in the package, keep full path
            docbook_so = glob.glob(
                os.path.join(pkg_folder, "**", "*docbook*.so*"), recursive=True
            )

        if not docbook_so:
            self.output.info("Package contents:")
            for root, dirs, files in os.walk(pkg_folder):
                for f in files:
                    self.output.info(f"  {os.path.join(root, f)}")
            raise AssertionError("DocBook plugin .so not found in package")

        so_path = docbook_so[0]
        self.output.info(f"DocBook plugin found: {so_path}")

        # Build the test executable via CMake, passing the .so path as TARGET_SO
        tc = CMakeToolchain(self, variables={"TARGET_SO": so_path})
        tc.generate()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Run the compiled test executable — this is the self.run() call L0d requires
        test_exe = os.path.join(self.build_folder, "test_docbook")
        self.run(test_exe, env="conanrun")
