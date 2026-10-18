#!/usr/bin/env python3
"""Siconos C/C++ libraries with Fortran solvers on OHOS arm64.

Uses the released Flang tool package, OpenBLAS and upstream bundled
CXSparse/LDL. All registered C/C++/Fortran tests run during build().
Python bindings are outside this package's scope.
"""
import os
import subprocess
import json
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

required_conan_version = ">=2.0"


class SiconosConan(ConanFile):
    name = "siconos"
    version = "4.4.0"
    description = ("Siconos: an open source scientific software for modeling "
                   "and simulating nonsmooth dynamical systems")
    license = ("Apache-2.0", "LGPL-2.1-or-later", "BSL-1.0", "MIT", "BSD-3-Clause")
    homepage = "https://github.com/siconos/siconos"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True],
        "fPIC": [True, False],
        "with_tests": [True],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_tests": True,
    }

    # The upstream default native components; io provides MechanicsIO.
    _components = "externals;numerics;kernel;control;mechanics;io"

    def export_sources(self):
        export_conandata_patches(self)
        for pattern in ("*.py", "*.json"):
            copy(self, pattern, src=os.path.join(self.recipe_folder, "validation"),
                 dst=os.path.join(self.export_sources_folder, "validation"))

    def requirements(self):
        self.requires("gmp/6.3.0.1", transitive_headers=True)
        self.requires("boost/1.84.0", transitive_headers=True)
        self.requires("openblas/0.3.34", transitive_headers=True)

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")
        self.test_requires("cppunit/1.15.1")

    def validate(self):
        if str(self.settings.os) not in ("OHOS",) or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("This native OHOS Flang recipe targets OHOS/armv8")

    def layout(self):
        cmake_layout(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        source = self.conan_data["sources"][str(self.version)]
        try:
            get(self, **source, strip_root=True, retry=0)
        except ConanException:
            # Same official GitHub archive and pinned digest; codeload is
            # reachable from devices whose network cannot reach github.com.
            get(self, url="https://github.com/siconos/siconos/archive/refs/tags/4.4.0.tar.gz",
                sha256=source["sha256"], filename="siconos-4.4.0.tar.gz",
                strip_root=True, retry=0)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # The old nonsmooth sampled-control reference trajectories depend on
        # separate multiply/add rounding. Keep that contract on aarch64.
        tc.extra_cflags.append("-ffp-contract=off")
        tc.extra_cxxflags.append("-ffp-contract=off")
        tc.cache_variables["SICONOS_PUBLIC_BOOST_DEFINITIONS"] = ";".join(
            self.dependencies["boost"].cpp_info.aggregated_components().defines)
        # The source patches request the GMP/CppUnit modules explicitly,
        # including during CMake's automatic regeneration.
        tc.cache_variables["GMP_ROOT"] = self.dependencies["gmp"].package_folder
        if self.options.with_tests:
            tc.cache_variables["CPPUNIT_ROOT"] = self.dependencies["cppunit"].package_folder
            tc.cache_variables["CPPUNIT_INCLUDE_DIR"] = os.path.join(self.dependencies["cppunit"].package_folder, "include")
        flang = self.dependencies.build["flang-ohos"].package_folder
        tc.cache_variables["CMAKE_Fortran_COMPILER"] = os.path.join(flang, "bin", "flang")
        cc = self.conf.get("tools.build:compiler_executables", check_type=dict)["c"]
        resource = os.path.realpath(subprocess.check_output(
            [cc, "-print-resource-dir"], text=True).strip())
        llvm = os.path.dirname(os.path.dirname(os.path.dirname(resource)))
        sysroot = self.conf.get("tools.build:sysroot") or os.path.join(os.path.dirname(llvm), "sysroot")
        if not os.path.isdir(resource) or not os.path.isdir(sysroot):
            raise ConanInvalidConfiguration("Cannot locate OHOS SDK from compiler resource directory: " + resource)
        tc.cache_variables["CMAKE_Fortran_FLAGS"] = (
            '--target=aarch64-unknown-linux-ohos --sysroot="{}" '
            '-resource-dir="{}" -I"{}" -ffp-contract=off'.format(
                sysroot, resource, os.path.join(flang, "include", "flang")))
        tc.extra_exelinkflags.append('-L{}'.format(os.path.join(llvm, "lib", "aarch64-linux-ohos")))
        tc.extra_sharedlinkflags.append('-L{}'.format(os.path.join(llvm, "lib", "aarch64-linux-ohos")))
        # siconos declares these through option()/set(CACHE) in
        # cmake/default_options.cmake, which is included *before* project();
        # a plain cache set from the toolchain would not override it, so use
        # FORCE cache variables.
        tc.cache_variables["COMPONENTS"] = self._components
        tc.cache_variables["WITH_CXX"] = True
        tc.cache_variables["WITH_FORTRAN"] = True
        tc.cache_variables["WITH_PYTHON_WRAPPER"] = False
        tc.cache_variables["WITH_SERIALIZATION"] = False
        tc.cache_variables["WITH_SYSTEM_SUITESPARSE"] = False
        tc.cache_variables["INSTALL_EXTERNAL_HEADERS"] = True
        tc.cache_variables["WITH_TESTING"] = bool(self.options.with_tests)
        tc.cache_variables["WITH_OPENMP"] = False
        tc.cache_variables["CMAKE_SKIP_RPATH"] = True
        tc.cache_variables["FORCE_SKIP_RPATH"] = True
        tc.cache_variables["WITH_UNSTABLE_TEST"] = False
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # CMake 4 removed compatibility with cmake_minimum_required < 3.5;
        # siconos asks for 3.11 but the policy floor must be explicit.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Use OpenBLAS for both BLAS and LAPACK; its CBLAS/LAPACKE headers are
        # what siconos' FindBLASDEV/FindLAPACKDEV modules look for.
        tc.cache_variables["BLA_VENDOR"] = "OpenBLAS"
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # The upstream tests capture this runtime environment at configure
        # time, adding all component build dirs when CMAKE_SKIP_RPATH is on.
        with VirtualRunEnv(self).vars().apply():
            cmake.configure()
            cmake.build(build_tool_args=["-j1"])
        if self.options.with_tests:
            self.run("ctest --show-only=json-v1 > upstream-inventory.json",
                     cwd=self.build_folder)
            rc = self.run("ctest -T Test --no-compress-output --output-on-failure --no-tests=error --timeout 200 "
                          "--parallel 1 --test-output-size-passed 10000000 "
                          "--test-output-size-failed 10000000 --output-junit upstream-raw.xml",
                          cwd=self.build_folder, ignore_errors=True)
            validation = os.path.join(self.source_folder, "validation")
            # New failures, changed case counts, exceptions, skipped tests,
            # missing output and abnormal exits are all blocking. Two exact
            # Linux-reproduced reference failures remain FAIL in the reports.
            self.run(shlex.join([sys.executable, os.path.join(validation, "summarize_upstream.py"),
                                 "--build", self.build_folder, "--ctest-exit-code", str(rc)]))
            self.run(shlex.join([sys.executable, os.path.join(validation, "trajectory_checks.py"),
                                 "--build", self.build_folder, "--output",
                                 os.path.join(self.build_folder, "trajectory-validation.json")]))
            with open(os.path.join(self.build_folder, "upstream-results.json")) as stream:
                result = json.load(stream)
            if result["failed"]:
                self.output.warning("Upstream reference tests are PARTIAL, not 100%: " +
                                    json.dumps(result["baseline_reproduced_failed_methods"]))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        for directory, filename in (("SuiteSparse", "LICENSE.txt"),
                                    ("numeric_bindings", "LICENSE_1_0.txt"),
                                    ("sort", "LICENSE.md"),
                                    ("netlib/dftemplates", "LICENSE")):
            copy(self, filename, src=os.path.join(self.source_folder, "externals", directory),
                 dst=os.path.join(self.package_folder, "licenses", directory))
        copy(self, "upstream-results.*", src=self.build_folder,
             dst=os.path.join(self.package_folder, "reports"))
        copy(self, "trajectory-validation.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "reports"))
        copy(self, "reference-policy.json", src=os.path.join(self.source_folder, "validation"),
             dst=os.path.join(self.package_folder, "reports"))

    def package_info(self):
        # The package also installs the real siconos example-compilation CLI.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "siconos")
        self.cpp_info.components["externals"].libs = ["siconos_externals"]
        self.cpp_info.components["numerics"].libs = ["siconos_numerics"]
        self.cpp_info.components["kernel"].libs = ["siconos_kernel"]
        self.cpp_info.components["control"].libs = ["siconos_control"]
        self.cpp_info.components["mechanics"].libs = ["siconos_mechanics"]
        self.cpp_info.components["io"].libs = ["siconos_io"]
        self.cpp_info.components["numerics"].requires = ["externals"]
        self.cpp_info.components["externals"].requires = ["openblas::openblas"]
        self.cpp_info.components["kernel"].requires = ["externals", "numerics"]
        self.cpp_info.components["control"].requires = ["kernel", "numerics"]
        self.cpp_info.components["mechanics"].requires = ["kernel", "numerics"]
        self.cpp_info.components["io"].requires = ["mechanics", "kernel"]
        for component in ("externals", "numerics", "kernel", "control", "mechanics", "io"):
            self.cpp_info.components[component].set_property("cmake_target_name", "Siconos::" + component)
            self.cpp_info.components[component].includedirs = ["include/siconos", "include/siconos/" + component]
        self.cpp_info.components["kernel"].requires += ["boost::boost_headers", "gmp::gmp"]
