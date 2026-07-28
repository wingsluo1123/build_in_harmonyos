#!/usr/bin/env python3
"""Conan recipe for Boost 1.90.0.1 compiled components.

The existing boost/1.90.0 archive is intentionally header-only. This revision
adds the compiled Boost libraries needed by downstream packages such as
FastNetMon while keeping the upstream source version at 1.90.0.
"""

import os

from conan import ConanFile
from conan.tools.files import copy, get


class BoostCompiledConan(ConanFile):
    name = "boost"
    version = "1.90.0.1"
    description = "Boost C++ Libraries 1.90.0 compiled component subset"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""
    topics = ("boost", "cpp", "thread", "serialization", "regex")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    _components = (
        "atomic",
        "chrono",
        "filesystem",
        "program_options",
        "regex",
        "serialization",
        "thread",
        "timer",
    )

    def layout(self):
        self.folders.source = "src"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _b2_executable(self):
        return "b2.exe" if self.settings.os == "Windows" else "./b2"

    def _b2_variant(self):
        build_type = str(self.settings.build_type)
        variants = {
            "Debug": "debug",
            "Release": "release",
            "RelWithDebInfo": "release",
            "MinSizeRel": "release",
        }
        return variants[build_type]

    def _bootstrap_command(self):
        if self.settings.os == "Windows":
            compiler = str(self.settings.compiler)
            toolset = "gcc" if compiler == "gcc" else "clang" if compiler == "clang" else ""
            return "bootstrap.bat" + (f" {toolset}" if toolset else "")
        libraries = ",".join(self._components)
        return f"sh bootstrap.sh --with-libraries={libraries}"

    def _b2_common_args(self):
        link = "shared" if self.options.shared else "static"
        jobs = min(os.cpu_count() or 2, 8)
        address_model = "64" if str(self.settings.arch) in ("x86_64", "armv8", "armv8.3") else "32"
        args = [
            f"-j{jobs}",
            "--layout=system",
            f"variant={self._b2_variant()}",
            f"link={link}",
            f"address-model={address_model}",
            "threading=multi",
            "runtime-link=shared",
            "cxxstd=14",
        ]
        if self.settings.os != "Windows" and not self.options.shared and self.options.fPIC:
            args.append("cxxflags=-fPIC")
        for component in self._components:
            args.append(f"--with-{component}")
        return args

    def build(self):
        self.run(self._bootstrap_command(), cwd=self.source_folder)
        b2_args = " ".join(self._b2_common_args())
        self.run(f"{self._b2_executable()} {b2_args} stage", cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE_1_0.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        prefix = self.package_folder.replace("\\", "/")
        b2_args = " ".join(self._b2_common_args())
        self.run(f"{self._b2_executable()} {b2_args} --prefix=\"{prefix}\" install", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]

        header_info = self.cpp_info.components["boost"]
        header_info.set_property("cmake_target_name", "Boost::boost")
        header_info.set_property("cmake_file_name", "Boost")
        header_info.includedirs = ["include"]
        header_info.libdirs = []
        header_info.libs = []

        for component in self._components:
            info = self.cpp_info.components[component]
            info.set_property("cmake_target_name", f"Boost::{component}")
            info.set_property("cmake_file_name", "Boost")
            info.includedirs = ["include"]
            info.libdirs = ["lib"]
            info.libs = [f"boost_{component}"]

        self.cpp_info.components["chrono"].requires = ["atomic"]
        self.cpp_info.components["filesystem"].requires = ["atomic"]
        self.cpp_info.components["thread"].requires = ["chrono", "atomic"]
        self.cpp_info.components["timer"].requires = ["chrono"]

        if str(self.settings.os) in ("Linux", "OHOS", "FreeBSD"):
            self.cpp_info.components["thread"].system_libs.append("pthread")
