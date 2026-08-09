#!/usr/bin/env python3
"""Conan recipe — keyfinder-cli 1.2.0 (cmake)

keyfinder-cli is a command-line tool for musical key detection using
libkeyfinder and FFmpeg. It decodes audio files and estimates the
musical key.
"""
import os
import glob

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class KeyfinderCliConan(ConanFile):
    name = "keyfinder-cli"
    version = "1.2.0"
    package_type = "application"
    license = "MIT"
    homepage = "https://github.com/EvanPurkhiser/keyfinder-cli"
    url = "https://github.com/EvanPurkhiser/keyfinder-cli"
    description = "Command-line tool for musical key detection using libkeyfinder and FFmpeg."
    topics = ("keyfinder", "music", "audio", "key-detection", "cli")
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libkeyfinder/2.2.8")
        self.requires("ffmpeg/7.1.5")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.generate()
        CMakeDeps(self).generate()
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        if self.settings.os != "OHOS":
            return
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        targets = []
        for name in os.listdir(bindir):
            p = os.path.join(bindir, name)
            if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
