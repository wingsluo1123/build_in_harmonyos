#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake


class LibxsltTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("libxml2/2.15.3")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not cross_building(self):
            cmake = CMake(self)
            cmake.test()
        dep = self.dependencies["libxslt"]
        exe = "xsltproc.exe" if self.settings.os == "Windows" else "xsltproc"
        xsltproc = os.path.join(dep.package_folder, "bin", exe)
        if cross_building(self):
            self.output.info("cross-building: xsltproc run test skipped")
            return
        xsl = os.path.join(self.source_folder, "test.xsl")
        xml = os.path.join(self.source_folder, "test.xml")
        self.run('"{}" "{}" "{}"'.format(xsltproc, xsl, xml), env="conanrun")
