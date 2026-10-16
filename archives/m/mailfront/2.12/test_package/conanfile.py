#!/usr/bin/env python3
"""Consumer and target-runtime tests for mailfront 2.12."""

import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv


class MailfrontTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("cvm/0.97")
        self.requires("bglibs/2.04")
        self.requires("openssl/3.5.8.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.cache_variables["MAILFRONT_INCLUDE_DIR"] = os.path.join(
            self.dependencies["mailfront"].package_folder,
            "include",
        )
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _tool(self, name):
        with VirtualBuildEnv(self).vars().apply():
            result = shutil.which(name)
        if not result:
            raise ConanException("required OHOS tool is missing: " + name)
        return result

    def _sign(self, path):
        objcopy = self._tool("llvm-objcopy")
        signer = self._tool("binary-sign-tool")
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", path, "-selfSign", "1"],
            check=True,
        )

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: target-runtime consumer test deferred")
            return

        consumer = os.path.join(self.cpp.build.bindir, "consumer")
        auth_module = os.path.join(self.cpp.build.bindir, "mailfront_testcvm")
        if str(self.settings.os) == "OHOS":
            self._sign(consumer)
            self._sign(auth_module)
        self.run(consumer, env="conanrun")

        package = self.dependencies["mailfront"].package_folder
        openssl = os.path.join(
            self.dependencies["openssl"].package_folder, "bin", "openssl"
        )
        mailfront = os.path.join(package, "bin", "mailfront")
        module_dir = os.path.join(package, "lib", "mailfront")
        script = os.path.join(self.source_folder, "starttls_matrix.py")
        command = [
            shutil.which("python3") or "python3",
            script,
            "--mailfront",
            mailfront,
            "--modules",
            module_dir,
            "--auth-module",
            auth_module,
            "--openssl",
            openssl,
            "--expect",
            "fixed",
        ]
        self.run(" ".join('"{}"'.format(item) for item in command), env="conanrun")

        readelf = self._tool("llvm-readelf")
        elf_paths = [mailfront] + sorted(glob.glob(os.path.join(module_dir, "*.so")))
        for path in elf_paths:
            sections = subprocess.run(
                [readelf, "-SW", path], capture_output=True, text=True, check=True
            ).stdout
            dynamic = subprocess.run(
                [readelf, "-d", path], capture_output=True, text=True, check=True
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanException("ELF must have exactly one .codesign: " + path)
            if "RPATH" in dynamic or "RUNPATH" in dynamic:
                raise ConanException("ELF contains RPATH/RUNPATH: " + path)
