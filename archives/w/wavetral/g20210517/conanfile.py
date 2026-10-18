#!/usr/bin/env python3
"""Conan recipe for wavetral g20210517."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class WavetralConan(ConanFile):
    name = "wavetral"
    version = "g20210517"
    description = "Convert single-cycle audio waveforms and spectra between synthesizer formats"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/jeanette-c/wavetral"
    url = "https://github.com/jeanette-c/wavetral"
    topics = ("audio", "waveform", "spectrum", "converter")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.90.0.4")
        self.requires("fftw/3.3.11")
        self.requires("libsndfile/1.2.2")
        self.requires("libsamplerate/0.2.2")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} is not supported (only Linux/OHOS)")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="wavetral-g20210517.tar.gz")

    def generate(self):
        CMakeDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # Upstream CMake checks legacy Boost_* variables after find_package().
        # Conan config mode exports imported targets instead, so bridge both.
        tc.cache_variables["Boost_PROGRAM_OPTIONS_FOUND"] = True
        tc.cache_variables["Boost_FILESYSTEM_FOUND"] = True
        tc.cache_variables["Boost_SYSTEM_FOUND"] = True
        tc.cache_variables["Boost_PROGRAM_OPTIONS_LIBRARY"] = "Boost::program_options"
        tc.cache_variables["Boost_FILESYSTEM_LIBRARY"] = "Boost::filesystem"
        tc.cache_variables["Boost_SYSTEM_LIBRARY"] = "Boost::system"
        fftw = self.dependencies.get("fftw")
        if fftw and fftw.package_folder:
            fftw_libdir = os.path.join(fftw.package_folder, "lib")
            tc.cache_variables["FFTW3_LIBRARIES"] = ";".join([
                os.path.join(fftw_libdir, "libfftw3.so"),
                os.path.join(fftw_libdir, "libfftw3_threads.so"),
            ])
            tc.cache_variables["FFTW3_INCLUDE_DIRS"] = os.path.join(
                fftw.package_folder, "include")
        samplerate = self.dependencies.get("libsamplerate")
        if samplerate and samplerate.package_folder:
            tc.cache_variables["LIBSAMPLERATE_FOUND"] = True
            tc.cache_variables["LIBSAMPLERATE_LIBRARY"] = "libsamplerate::libsamplerate"
            tc.cache_variables["LIBSAMPLERATE_INCLUDE_DIR"] = os.path.join(
                samplerate.package_folder, "include")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._sign_ohos_executable()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []

    def _sign_ohos_executable(self):
        """Sign the packaged ELF when building on a native HarmonyOS worker."""
        if str(self.settings.os) != "OHOS" or not can_run(self):
            return
        exe = os.path.join(self.package_folder, "bin", "wavetral")
        if not os.path.isfile(exe):
            raise ConanInvalidConfiguration("wavetral executable was not packaged")
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            raise ConanInvalidConfiguration("OHOS ELF signing tools are missing")
        self.run(f'{objcopy} --remove-section .codesign "{exe}" 2>/dev/null || true')
        self.run(f'{signer} sign -inFile "{exe}" -outFile "{exe}" -selfSign 1')
