#!/usr/bin/env python3
"""Conan recipe for qmidictl 1.0.2 — Qt6 MIDI remote controller for HarmonyOS PC.

qmidictl is a Qt6 (Core/Gui/Widgets/Svg/Network) desktop GUI application that
sends MIDI data over the network using UDP/IP multicast.  Upstream ships a
CMake build (>= 3.15) with AUTOMOC/AUTOUIC/AUTORCC; the produced executable is
installed to ``bin/`` (plus icons, .desktop and man pages under ``share/``).

Key adaptations (details in notes.md):
  * E438: qtbase ships its own relocatable Qt6Config.cmake (cmake_find_mode
    "none"), so the qtbase / qtsvg package folders are handed to CMake through
    CMAKE_PREFIX_PATH, Qt6_DIR, Qt6Svg_DIR and CMAKE_MODULE_PATH
    (Platform/HarmonyOS.cmake includes the Linux platform).
  * R38: the package produces a CLI entry (``qmidictl``), so the software-level
    commands.json declares it.
  * R34/R51: upstream ships no automated tests at all (71 files, no tests/ tree
    and no CTest registration), so test_package/ carries the whole L1
    verification with a real exec probe against the packaged binary.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class QmidictlConan(ConanFile):
    name = "qmidictl"
    version = "1.0.2"
    description = (
        "MIDI remote controller application that sends MIDI data over the"
        " network using UDP/IP multicast"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://qmidictl.sourceforge.io"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qtbase provides Core/Gui/Widgets/Network; the Svg component used for
        # the application icons comes from the separate qtsvg package.
        # R35: qtsvg/6.11.1.1 pins qtbase/6.11.1.3 in its own recipe, so the
        # graph only resolves with qtbase/6.11.1.3 (both revisions were probed
        # for published binaries with `conan install --build=never`).
        self.requires("qtbase/6.11.1.3")
        self.requires("qtsvg/6.11.1.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qmidictl supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def generate(self):
        qtbase_prefix = self.dependencies["qtbase"].package_folder
        qtsvg_prefix = self.dependencies["qtsvg"].package_folder

        tc = CMakeToolchain(self)
        # E438: qtbase ships its own relocatable Qt6Config.cmake, expose the
        # package folders directly (CMakeDeps does not export Qt6 targets).
        tc.cache_variables["CMAKE_PREFIX_PATH"] = (
            qtbase_prefix + os.pathsep + qtsvg_prefix
        )
        # Set Qt6_DIR / Qt6Svg_DIR directly so every nested CMakeLists.txt
        # finds Qt6Config.cmake / Qt6SvgConfig.cmake.
        tc.cache_variables["Qt6_DIR"] = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6"
        )
        tc.cache_variables["Qt6Svg_DIR"] = os.path.join(
            qtsvg_prefix, "lib", "cmake", "Qt6Svg"
        )
        # Platform/HarmonyOS.cmake (which includes Linux) lives under qtbase's
        # cmake dir; without it CMake treats HarmonyOS as an unknown platform.
        tc.cache_variables["CMAKE_MODULE_PATH"] = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6", "platforms"
        )
        # Upstream pins the target to C++17 (src/CMakeLists.txt).
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "17"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # E077: the OHOS kernel refuses to exec an unsigned ELF (execve EPERM,
        # rc=126), which would make the test_package exec probe meaningless;
        # sign the GUI binary at packaging time (qastools/1.4.0 precedent).
        binary = os.path.join(self.package_folder, "bin", "qmidictl")
        if os.path.isfile(binary):
            os.chmod(binary, 0o755)
            self._sign_ohos_binary(binary)

    def _sign_ohos_binary(self, path):
        if str(self.settings.os) != "OHOS":
            return

        signer = self.conf.get("user.ohos:sign_tool", default="", check_type=str)
        signer = (
            signer
            or os.environ.get("OHOS_SIGN_TOOL", "")
            or shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool is unavailable; skipping OHOS ELF signing"
            )
            return

        objcopy = self.conf.get("user.ohos:objcopy", default="", check_type=str)
        objcopy = (
            objcopy
            or os.environ.get("OHOS_OBJCOPY", "")
            or shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        if os.path.isfile(objcopy):
            self.run(
                f'"{objcopy}" --remove-section .codesign "{path}"',
                ignore_errors=True,
            )

        signed = f"{path}.signed"
        self.run(
            f'"{signer}" sign -inFile "{path}" '
            f'-outFile "{signed}" -selfSign 1'
        )
        if not os.path.isfile(signed):
            raise ConanException(f"binary-sign-tool produced no output for {path}")
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
