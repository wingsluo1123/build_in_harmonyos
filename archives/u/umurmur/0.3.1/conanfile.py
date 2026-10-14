#!/usr/bin/env python3
"""Conan recipe for uMurmur 0.3.1, a minimal Mumble server."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class UmurmurConan(ConanFile):
    name = "umurmur"
    version = "0.3.1"
    description = "Minimal Mumble-compatible voice chat server"
    license = "BSD-3-Clause"
    homepage = "https://github.com/umurmur/umurmur"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("mumble", "voice-chat", "tls", "protobuf-c", "server")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "uMurmur supports only Linux and OHOS in this recipe"
            )

    def requirements(self):
        self.requires("libconfig/1.8")
        self.requires("protobuf-c/1.5.1")
        self.requires("openssl/3.5.8.1")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["SSL"] = "openssl"
        toolchain.variables["USE_SHAREDMEMORY_API"] = False
        toolchain.variables["BUILD_UMURMUR_MONITOR"] = False
        toolchain.variables["BUILD_NUMURMON"] = False
        toolchain.variables["CMAKE_SKIP_RPATH"] = True
        toolchain.variables["CMAKE_INSTALL_RPATH"] = ""
        toolchain.variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = False
        for source_path in (self.source_folder, self.build_folder):
            mapped_path = "/usr/src/umurmur-0.3.1"
            toolchain.extra_cflags.extend(
                [
                    f"-ffile-prefix-map={source_path}={mapped_path}",
                    f"-fmacro-prefix-map={source_path}={mapped_path}",
                ]
            )
        toolchain.generate()

    def build(self):
        self._apply_patches()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _apply_patches(self):
        """Apply the state-transition patch with Git's zero-context support."""
        patch_table = self.conan_data.get("patches", {})
        version_key = str(self.version)
        all_patches = patch_table.get(version_key, [])
        deferred_name = "patches/0003-flush-first-frame-after-tls-handshake.patch"
        patch_table[version_key] = [
            entry for entry in all_patches if entry.get("patch_file") != deferred_name
        ]
        try:
            apply_conandata_patches(self)
        finally:
            patch_table[version_key] = all_patches

        git = shutil.which("git")
        if not git:
            raise ConanException("git is required to apply the TLS state-transition patch")
        subprocess.run(
            [
                git,
                "apply",
                "--unidiff-zero",
                os.path.join(self.export_sources_folder, deferred_name),
            ],
            cwd=self.source_folder,
            check=True,
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if self.settings.os == "OHOS":
            self._sign_elf(os.path.join(self.package_folder, "sbin", "umurmurd"))
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def _sign_elf(self, binary):
        """Sign the final installed ELF after CMake has finished rewriting it."""
        with VirtualBuildEnv(self).vars().apply():
            objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
            readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
            strip = shutil.which("llvm-strip") or shutil.which("strip")
            signer = shutil.which("binary-sign-tool")
            if not objcopy or not readelf or not strip or not signer:
                raise ConanException(
                    "objcopy, readelf, strip and binary-sign-tool are required for OHOS executables"
                )

            subprocess.run([strip, "--strip-debug", binary], check=True)
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", binary],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            result = subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    binary,
                    "-outFile",
                    binary,
                    "-selfSign",
                    "1",
                ],
                capture_output=True,
                text=True,
            )
            sections = subprocess.run(
                [readelf, "-SW", binary], capture_output=True, text=True, check=True
            ).stdout
            dynamic = subprocess.run(
                [readelf, "-d", binary], capture_output=True, text=True, check=True
            ).stdout
        with open(binary, "rb") as binary_file:
            binary_data = binary_file.read()
        leaked_paths = [
            path
            for path in (self.build_folder, self.source_folder, self.package_folder)
            if path and os.fsencode(path) in binary_data
        ]
        if result.returncode != 0 or sections.count(".codesign") != 1:
            raise ConanException(
                "failed to sign umurmurd: " + (result.stderr or result.stdout)
            )
        if "RPATH" in dynamic or "RUNPATH" in dynamic:
            raise ConanException("packaged umurmurd contains an RPATH/RUNPATH")
        if b".conan2" in binary_data or leaked_paths:
            raise ConanException(
                "packaged umurmurd contains Conan/build paths: " + ", ".join(leaked_paths)
            )
        os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["sbin"]
        self.cpp_info.libs = []
