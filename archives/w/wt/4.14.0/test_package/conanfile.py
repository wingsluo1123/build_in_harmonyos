#!/usr/bin/env python3
"""Conan test package for Wt 4.14.0.

Real end-to-end consumer check (the upstream testsuite harness Wt::Test is
not shipped in this package: it was disabled at configure time to keep the
dependency face minimal, and it drives network-dependent scenarios that a
CI sandbox cannot run). The test builds a WServer application against the
packaged wt + wthttp libraries, serves one page over plain HTTP on the
loopback interface and fetches it at socket level, asserting both the HTTP
status line and the application marker.
"""

import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class WtTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake >= 4 workers break the compiler check on the OHOS-adapted
        # CMAKE_SYSTEM_NAME=HarmonyOS mapping (libsoundio 48c47b83 precedent).
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8"
                else str(self.settings.arch)
            )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException(f"Missing consumer executable: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".wt-signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed consumer has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    def test(self):
        if not can_run(self):
            return
        executable = os.path.join(self.cpp.build.bindir, "test_wt")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(executable)
        # Runtime env (kwidgetsaddons5 / kcontacts5 precedent): the sandbox
        # LD_LIBRARY_PATH can carry an incompatible libc++_shared.so that
        # shadows the system copy and breaks relocation (__gxx_personality_v0
        # etc.); prepend the dependency lib dirs, /system/lib64 and the OHOS
        # toolchain libs so the musl-compatible copies win.
        run_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                run_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        # WServer reads its configuration from WT_CONFIG_XML; the packaged
        # copy ships under etc/wt/ in the wt package folder.
        wt_pkg = self.dependencies.get("wt")
        if wt_pkg and wt_pkg.package_folder:
            run_env.define(
                "WT_CONFIG_XML",
                os.path.join(
                    wt_pkg.package_folder, "etc", "wt", "wt_config.xml"
                ),
            )
        if str(self.settings.os) == "OHOS":
            run_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/"
                    "llvm/lib*"
                )
            ):
                if os.path.isdir(llvm_lib):
                    run_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        with run_env.vars(self).apply():
            self.run(f'"{executable}"')
