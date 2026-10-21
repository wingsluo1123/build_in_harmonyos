#!/usr/bin/env python3
"""Conan recipe for SOAPsnp 1.03 using the original Makefile."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class SoapsnpConan(ConanFile):
    name = "soapsnp"
    version = "1.03"
    description = "Consensus genotype calling from FASTA and sorted SOAP alignments"
    license = "GPL-3.0-or-later"
    homepage = "https://soap.genomics.org.cn/soapsnp.html"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.84.0")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        toolchain = AutotoolsToolchain(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        cxx = compilers.get("cpp", "c++")
        boost = self.dependencies["boost"].cpp_info
        zlib = self.dependencies["zlib"].cpp_info
        includes = boost.components["boost_headers"].includedirs + zlib.includedirs
        archives = [os.path.join(boost.components["boost_iostreams"].libdirs[0],
                                 "libboost_iostreams.a")]
        archives += [os.path.join(zlib.libdirs[0], "lib" + lib + ".a")
                     for lib in zlib.libs]
        if any(not os.path.isfile(path) for path in archives):
            raise ConanInvalidConfiguration("Published dependency static archive missing")
        cxxflags = toolchain.cxxflags + ["-fomit-frame-pointer", "-ffast-math",
                                        "-funroll-loops",
                                        "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        cxxflags += ["-I" + shlex.quote(path) for path in includes]
        # Full paths prevent SDK search directories from selecting system libz.so.
        ldflags = toolchain.ldflags + [shlex.quote(path) for path in archives]
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("make -j1 -C {} CXX={} CXXFLAGS={} LFLAGS={} SHELL={}".format(
            shlex.quote(self.source_folder), shlex.quote(cxx),
            shlex.quote(" ".join(cxxflags)), shlex.quote(" ".join(ldflags)),
            shlex.quote(shell)))
        # Original makefile: all/objects/clean only; no upstream test suite.
        # Installed CLI integration tests run through test_package.

    def package(self):
        copy(self, "soapsnp", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "readme", self.source_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
