#!/usr/bin/env python3
"""Build and test the default Viskores CPU libraries on HarmonyOS PC."""

import json
import os
import shlex
import xml.etree.ElementTree as ET

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, collect_libs, copy,
                               export_conandata_patches, get)


class ViskoresConan(ConanFile):
    name = "viskores"
    version = "1.1.1"
    description = "Portable data-parallel scientific visualization algorithms"
    homepage = "https://github.com/Viskores/viskores"
    license = "BSD-3-Clause"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def validate(self):
        if not self.options.shared:
            raise ConanInvalidConfiguration("This adaptation validates shared libraries")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src", generator="Ninja")

    def _get_archive(self, entry, destination):
        args = dict(entry)
        args.pop("commit", None)
        fallback = args.pop("fallback_url")
        try:
            get(self, **args, destination=destination, strip_root=True)
        except ConanException:
            # Same official GitHub archive bytes, reachable on the device.
            # The primary scalar URL remains eligible for CI mirror injection.
            self.output.warning("Primary archive unavailable; trying official codeload")
            args["url"] = fallback
            get(self, **args, destination=destination, strip_root=True,
                filename="viskores-source.tar.gz")

    def source(self):
        self._get_archive(self.conan_data["sources"], self.source_folder)
        self._get_archive(self.conan_data["test_data"],
                          os.path.join(self.source_folder, "data"))

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        if self.settings.os in ("Linux", "OHOS"):
            tc.blocks["generic_system"].values["cmake_system_name"] = "Linux"
            # Install must preserve the original linker bytes on HarmonyOS.
            # bin/../lib serves test programs; lib/../lib serves shared modules.
            tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
            tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN/../lib"
        tc.variables["BUILD_SHARED_LIBS"] = True
        tc.variables["Viskores_ENABLE_TESTING"] = True
        tc.variables["Viskores_ENABLE_RENDERING"] = True
        tc.variables["Viskores_ENABLE_CUDA"] = False
        tc.variables["Viskores_ENABLE_KOKKOS"] = False
        tc.variables["Viskores_ENABLE_MPI"] = False
        tc.variables["Viskores_ENABLE_TBB"] = False
        tc.variables["Viskores_ENABLE_OPENMP"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # Template-heavy translation units need bounded memory on the 32GB PC.
        self.run("cmake --build . --parallel 4", env="conanbuild")
        inventory_file = os.path.join(self.build_folder, "upstream-inventory.json")
        with open(inventory_file, "w", encoding="utf-8") as stream:
            self.run("ctest --show-only=json-v1", stdout=stream, env="conanbuild")
        with open(inventory_file, encoding="utf-8") as stream:
            expected = {test["name"] for test in json.load(stream)["tests"]}
        result_file = os.path.join(self.build_folder, "upstream-tests.xml")
        self.run("ctest --no-tests=error --output-on-failure -j2 --timeout 180 --output-junit "
                 + shlex.quote(result_file), env="conanbuild")
        tree = ET.parse(result_file).getroot()
        cases = list(tree.iter("testcase"))
        failed = sum(case.find("failure") is not None or
                     case.find("error") is not None for case in cases)
        skipped = sum(case.find("skipped") is not None for case in cases)
        actual = {case.get("name") for case in cases}
        if not expected or actual != expected or len(cases) != len(expected):
            raise ConanException("CTest execution does not match its discovery inventory")
        if failed or len(cases) == skipped:
            raise ConanException("CTest reported failures or no executed tests")
        summary = {"status": "partial" if skipped else "passed", "discovered": len(cases),
                   "executed": len(cases) - skipped,
                   "passed": len(cases) - failed - skipped,
                   "failed": failed, "skipped": skipped}
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(summary))

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Keep upstream's complete target graph, including filter submodules
        # and bundled DIY, rather than flattening it into an incomplete target.
        self.cpp_info.set_property("cmake_file_name", "Viskores")
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = ["lib/cmake/viskores-1.1"]
        self.cpp_info.includedirs = ["include/viskores-1.1"]
        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.system_libs = ["pthread", "dl"]
