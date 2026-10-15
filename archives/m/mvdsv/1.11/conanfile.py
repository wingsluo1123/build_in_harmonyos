#!/usr/bin/env python3
"""Conan recipe — MVDSV 1.11 (CMake)."""

import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class MvdsvConan(ConanFile):
    name = "mvdsv"
    version = "1.11"
    description = "High-performance QuakeWorld dedicated server"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/QW-Group/mvdsv"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("quakeworld", "game-server", "networking")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration("This MVDSV recipe targets OHOS only")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        sources = self.conan_data["sources"]
        get(self, **sources["mvdsv"], strip_root=True)
        get(
            self,
            **sources["qwprot"],
            destination=os.path.join(self.source_folder, "src", "qwprot"),
            strip_root=True,
        )

    def generate(self):
        # The OHOS worker has a deliberately small per-user process limit.
        # Ninja avoids Make's extra recursive shell layer during CMake compiler
        # probes, while the serialized build keeps peak process use bounded.
        toolchain = CMakeToolchain(self, generator="Ninja")
        toolchain.variables["BUILD_TESTING"] = True
        toolchain.variables["CMAKE_DISABLE_FIND_PACKAGE_CURL"] = True
        toolchain.variables["PCRE_FOUND"] = False
        toolchain.variables["CMAKE_SKIP_RPATH"] = True
        toolchain.variables["CMAKE_INSTALL_RPATH"] = ""
        toolchain.variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = False
        mapped_path = "/usr/src/mvdsv-1.11"
        for source_path in (self.source_folder, self.build_folder):
            toolchain.extra_cflags.extend(
                [
                    f"-ffile-prefix-map={source_path}={mapped_path}",
                    f"-fmacro-prefix-map={source_path}={mapped_path}",
                ]
            )
        toolchain.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])
        runner = self.conf.get("user.libminini:qemu_runner", default="")
        if can_run(self) and not runner:
            queue_test = os.path.join(self.build_folder, "tcp_queue_test")
            if self.settings.os == "OHOS":
                self._sign_elf(queue_test, strip_binary=False)
            ctest = shutil.which("ctest") or "ctest"
            self.run(
                f'"{ctest}" --test-dir "{self.build_folder}" '
                "--output-on-failure",
                env="conanrun",
            )

    def package(self):
        copy(
            self,
            "mvdsv",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        binary = os.path.join(self.package_folder, "bin", "mvdsv")
        if self.settings.os == "OHOS":
            self._sign_elf(binary, strip_binary=True)
        copy(
            self,
            "LICENSE.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def _tool_candidates(self, name):
        executable = shutil.which(name)
        if executable:
            yield executable

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compilers.get("c") if compilers else None
        if compiler:
            compiler_path = Path(compiler).resolve()
            yield str(compiler_path.parent / name)
            sdk_root = compiler_path.parents[3]
            if name == "binary-sign-tool":
                yield str(sdk_root / "toolchains" / "lib" / name)

    def _find_tool(self, name):
        for candidate in self._tool_candidates(name):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        raise ConanException(f"required OHOS tool not found: {name}")

    def _sign_elf(self, binary, strip_binary):
        with VirtualBuildEnv(self).vars().apply():
            objcopy = self._find_tool("llvm-objcopy")
            readelf = self._find_tool("llvm-readelf")
            signer = self._find_tool("binary-sign-tool")
            if strip_binary:
                subprocess.run([self._find_tool("llvm-strip"), "--strip-debug", binary], check=True)
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

        binary_data = Path(binary).read_bytes()
        leaked_paths = [
            path
            for path in (self.build_folder, self.source_folder, self.package_folder)
            if path and os.fsencode(path) in binary_data
        ]
        if result.returncode != 0 or sections.count(".codesign") != 1:
            raise ConanException("failed to sign MVDSV ELF: " + (result.stderr or result.stdout))
        if "RPATH" in dynamic or "RUNPATH" in dynamic:
            raise ConanException("packaged MVDSV contains RPATH/RUNPATH")
        if b".conan2" in binary_data or leaked_paths:
            raise ConanException("packaged MVDSV contains a build-host path")
        os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
