#!/usr/bin/env python3
"""Conan recipe for DynamoRIO (dynamic binary instrumentation framework) on OHOS PC.

Upstream master @ 2026-08-11 (= version 11.91.20676, see conandata.yml) adapted to
the OHOS PC (aarch64, musl, clang 15) toolchain.  The adaptation is carried entirely
by conandata patches; see notes.md for the failure catalogue and reports/ for the
evidence.
"""
import importlib.util
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class DynamoRIOConan(ConanFile):
    name = "dynamorio"
    version = "11.91.20676"
    description = "Dynamic binary instrumentation framework (DBI engine: runtime code rewriting, code cache, fragment scheduling)"
    license = "BSD-3-Clause"
    homepage = "https://dynamorio.org/"
    url = "https://github.com/DynamoRIO/dynamorio"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # DynamoRIO always builds both the shared engine (libdynamorio.so, required by
    # the launcher and by any dynamically linked client) and the static libraries
    # (libdynamorio_static.a, used by the standalone/embedded form), so the option
    # is accepted for Conan package-type conformance and consumers are expected to
    # use find_package(DynamoRIO).
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "ohos_resign.py", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        basic_layout(self, src_folder="src", build_folder="build")

    def requirements(self):
        # zlib is required by the elfutils copy that ext/drsyms builds on 64-bit
        # Linux-like targets (CMakeLists.txt: "zlib not found but required to build
        # drsyms_static on Linux").
        self.requires("zlib/1.3.1.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("dynamorio is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="dynamorio-11.91.20676.tar.gz")
        # The source archive has no submodule contents: fetch the pinned elfutils.
        get(self, **self.conan_data["elfutils"], strip_root=True,
            filename="elfutils.tar.gz", destination="third_party/elfutils")

    def generate(self):
        tc = CMakeToolchain(self)
        # This profile is not a cross-build (the OHOS toolchain runs natively on
        # the OHOS host), so Conan does not emit CMAKE_SYSTEM_NAME.  DynamoRIO needs
        # it: without it CMake does not define UNIX and the build takes the Windows
        # branch (looking for mc.exe).  CMake maps OHOS to Platform/Linux.
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
            "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch))
        # The upstream regression suite is not built by the recipe: it is large
        # (hundreds of extra targets) and the suite's own contract is to drive
        # DynamoRIO's injected execution mode.  The measured upstream results
        # (ctest 57/417, see notes.md) were obtained locally with the suite
        # enabled; test_package/ carries the consumer-side smoke test instead.
        tc.cache_variables["BUILD_TESTS"] = False
        tc.cache_variables["BUILD_DOCS"] = False
        # Report the packaged version from the built artifacts: without a .git
        # directory DR's version computation degrades to patchlevel 0.
        tc.cache_variables["VERSION_NUMBER"] = str(self.version)
        if self.settings.os == "OHOS":
            # Target musl libc semantics explicitly: the build host is not used to
            # infer them when cross-compiling.
            tc.cache_variables["DR_TARGET_MUSL"] = True
            # OHOS refuses to execute an ELF whose .codesign record does not match
            # the file, and the post-link objcopy/strip steps that DR performs to
            # split debug info invalidate that record.  Keep the linker output
            # untouched.
            tc.cache_variables["SPLIT_SYMBOLS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # CMAKE_SYSTEM_NAME has to be forced on the command line: keeping it in
        # tc.cache_variables is not enough because Conan owns that variable and
        # drops user overrides when the profile is not a cross-build.  Without it
        # CMake derives the system name from `uname -s` ("HarmonyOS"), for which
        # no platform module exists, so UNIX stays undefined and DynamoRIO takes
        # its Windows branch.  "OHOS" has a platform module that includes Linux.
        cli_args = []
        if self.settings.os == "OHOS":
            cli_args = ["-DCMAKE_SYSTEM_NAME=OHOS",
                        "-DCMAKE_SYSTEM_PROCESSOR=aarch64"
                        if str(self.settings.arch) == "armv8" else
                        "-DCMAKE_SYSTEM_PROCESSOR=%s" % self.settings.arch]
        cmake.configure(cli_args=cli_args)
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # OHOS: the lld --code-sign pass produces an inconsistent .codesign record
        # when a link pulls in a large static archive, which is the case for every
        # executable linked against libdynamorio_static.a.  Re-generate the
        # signature so that the packaged tools are executable (no-op off OHOS).
        mod = self._load_resign_helper()
        if mod is not None:
            _repaired, problems = mod.resign_tree(self.package_folder)
            if problems:
                # Fail loudly rather than shipping binaries that OHOS will refuse
                # to execute (an unresolved signature used to be silent).
                raise ConanException(
                    "OHOS .codesign repair failed for %d file(s); the packaged "
                    "binaries would not be executable: %s"
                    % (len(problems), problems[:5]))

    def _load_resign_helper(self):
        for cand in (os.path.join(self.recipe_folder, "ohos_resign.py"),
                     os.path.join(self.export_sources_folder, "ohos_resign.py"),
                     os.path.join(self.source_folder, "ohos_resign.py")):
            if os.path.exists(cand):
                spec = importlib.util.spec_from_file_location("ohos_resign", cand)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
        self.output.warning("ohos_resign.py not found; package signature not repaired")
        return None

    def package_info(self):
        # DynamoRIO installs a DynamoRIOConfig.cmake package for consumers, plus a
        # "release" sub-directory on Unix.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib64/release", "lib64"]
        self.cpp_info.bindirs = ["bin64"]
        self.cpp_info.libs = ["dynamorio"]
        self.cpp_info.builddirs = ["cmake"]
        self.cpp_info.set_property("cmake_file_name", "DynamoRIO")
        self.cpp_info.set_property("cmake_target_name", "DynamoRIO::DynamoRIO")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin64"))
