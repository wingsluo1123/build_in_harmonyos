#!/usr/bin/env python3
"""Conan test_package — abiword-plugin-epub 3.0.8

L1 test: build test.c (dlopen + ABI symbol checks) against the installed
epub plugin .so and run it. Uses self.run() so the CI L0d gate sees a
real command execution, not a stub.
"""
import os
import glob

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain


class AbiwordPluginEpubTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # 注意: CMakeToolchain 不在 generators 属性声明——test() 里需手动实例化
    # 以设置 TARGET_SO 变量(见 P0 注释),若两者都有会报
    # "CMakeToolchain is declared in the generators attribute, but was
    # instantiated in the generate() method too"。CMakeDeps 保留属性声明。
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["abiword-plugin-epub"].package_folder
        plugin_dir = os.path.join(pkg_folder, "lib", "abiword", "plugins")

        # Find the epub plugin .so — keep full path to avoid basename/join mismatch
        epub_so = []
        if os.path.isdir(plugin_dir):
            epub_so = [os.path.join(plugin_dir, p) for p in os.listdir(plugin_dir)
                       if "epub" in p.lower() and p.endswith(".so")]

        if not epub_so:
            # Fallback: search anywhere in the package, keep full path
            epub_so = glob.glob(os.path.join(pkg_folder, "**", "*epub*.so*"), recursive=True)

        if not epub_so:
            self.output.info("Package contents:")
            for root, dirs, files in os.walk(pkg_folder):
                for f in files:
                    self.output.info(f"  {os.path.join(root, f)}")
            raise AssertionError("EPUB plugin .so not found in package")

        so_path = epub_so[0]
        self.output.info(f"EPUB plugin found: {so_path}")

        # Build the test executable via CMake, passing the .so path as TARGET_SO.
        # P0: Conan 2.x CMakeToolchain 不接受 variables= 构造参数(会抛 TypeError)，
        # 改为构造后用 tc.variables[...] 设置，再 generate()。
        tc = CMakeToolchain(self)
        tc.variables["TARGET_SO"] = so_path
        tc.generate()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Run the compiled test executable — this is the self.run() call L0d requires
        test_exe = os.path.join(self.build_folder, "test_epub")
        self.run(test_exe, env="conanrun")
