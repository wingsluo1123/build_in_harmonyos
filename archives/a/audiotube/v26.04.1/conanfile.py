#!/usr/bin/env python3
"""Conan recipe for audiotube v26.04.1 — ytm static library (OHOS minimal build).

audiotube is a KDE Kirigami-based music player with YouTube Music integration.
On OHOS, Qt6Qml/Quick/Multimedia/KF6Kirigami/FutureSQL6/QCoro6 are unavailable,
so only the ytm static library (pybind11 wrapper for ytmusicapi) is built via
the OHOS_MINIMAL_BUILD option.

Full audiotube executable requires missing GUI dependencies — reported for
expert analysis.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AudiotubeConan(ConanFile):
    name = "audiotube"
    version = "v26.04.1"
    description = "KDE Kirigami-based music player with YouTube Music integration (ytm library for OHOS)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/KDE/audiotube"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ecm/6.20.0")
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Ensure pybind11 is available before generate (needed for cmake config)
        self._ensure_pybind11()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["OHOS_MINIMAL_BUILD"] = "ON"
        # ECM needs qtpaths6 from qtbase — conan's CMakeDeps doesn't export
        # Qt6::qtpaths target, so set QUERY_EXECUTABLE directly
        qtbase = self.dependencies["qtbase"]
        qt_bin_dirs = qtbase.cpp_info.bindirs
        if qt_bin_dirs:
            program_paths = [os.path.join(qtbase.package_folder, d) for d in qt_bin_dirs]
            tc.variables["CMAKE_PROGRAM_PATH"] = ";".join(program_paths)
            # Also set QUERY_EXECUTABLE for ECM's ECMQueryQt module
            qtpaths = os.path.join(qtbase.package_folder, qt_bin_dirs[0], "qtpaths6")
            if os.path.exists(qtpaths):
                tc.variables["QUERY_EXECUTABLE"] = qtpaths
                tc.variables["_cli_option"] = "--query"
        # pybind11: locate cmake config dir
        pybind11_cmake_dir = self._get_pybind11_cmake_dir()
        if pybind11_cmake_dir:
            tc.variables["pybind11_DIR"] = pybind11_cmake_dir
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ytm"]
        self.cpp_info.includedirs = ["include/audiotube"]

    def _ensure_pybind11(self):
        """Install pybind11 via pip if not already available."""
        try:
            import pybind11  # noqa: F401
        except ImportError:
            subprocess.check_call(["pip3", "install", "pybind11==3.0.4"])

    def _get_pybind11_cmake_dir(self):
        """Return the cmake config directory for pybind11."""
        try:
            result = subprocess.run(
                ["python3", "-c", "import pybind11; print(pybind11.get_cmake_dir())"],
                capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
