#!/usr/bin/env python3
"""Conan test_package for OpenSceneGraph 3.6.5.

Tests that the OpenSceneGraph libraries are properly linked and functional.
Uses osg::Object and OpenThreads APIs to verify the package.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OpenscenegraphTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_openscenegraph")
        self.run(cmd, env="conanrun")
