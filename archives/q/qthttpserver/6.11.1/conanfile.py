#!/usr/bin/env python3
"""Conan recipe for Qt HTTP Server 6.11.1 on HarmonyOS PC."""

import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class QtHttpServerConan(ConanFile):
    name = "qthttpserver"
    version = "6.11.1"
    description = "Qt framework for embedding an HTTP server"
    license = "GPL-3.0-only AND BSD-3-Clause"
    homepage = "https://www.qt.io/"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires("qtbase-gui/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Qt modules use qtbase-gui's native Qt6Config.cmake and BuildInternals
        # files.  Point CMake at the dependency package instead of generating
        # an incomplete replacement config with CMakeDeps.
        qtbase_gui_prefix = self.dependencies["qtbase-gui"].package_folder
        tc.cache_variables["CMAKE_PREFIX_PATH"] = qtbase_gui_prefix
        tc.cache_variables.update(
            {
                "QT_BUILD_TESTS": False,
                "QT_BUILD_EXAMPLES": False,
                "QT_BUILD_BENCHMARKS": False,
                "QT_BUILD_DOCS": False,
                "BUILD_SHARED_LIBS": bool(self.options.shared),
                "QT_QMAKE_TARGET_MKSPEC": "harmonyos-clang",
            }
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        """Safely re-sign installed OHOS ELF shared objects."""
        libraries = self._installed_shared_libraries()
        if not libraries:
            return
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for library in libraries:
            original_mode = stat.S_IMODE(os.stat(library).st_mode)
            has_codesign = self._has_codesign_section(objdump, library)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(library)
            ) as temp_dir:
                sign_input = library
                if has_codesign:
                    sign_input = os.path.join(temp_dir, "unsigned")
                    shutil.copy2(library, sign_input)
                    self._run_tool(
                        [objcopy, "--remove-section", ".codesign", sign_input],
                        f"remove the old code signature from {library}",
                    )
                signed = os.path.join(temp_dir, "signed")
                self._run_tool(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        sign_input,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ],
                    f"sign {library}",
                )
                if not os.path.isfile(signed) or self._elf_type(signed) != 3:
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce an ELF shared object for {library}"
                    )
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {library}"
                    )
                os.replace(signed, library)
                os.chmod(library, original_mode)

    def _installed_shared_libraries(self):
        libraries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) == 3:  # ET_DYN
                    libraries.append(candidate)
        return sorted(libraries)

    @staticmethod
    def _elf_type(path):
        """Return the ELF e_type value, or None for a non-ELF file."""
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"Unable to inspect installed file {path}: {error}"
            ) from error
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            raise ConanInvalidConfiguration(
                f"Unsupported ELF byte order in installed file {path}"
            )
        return int.from_bytes(header[16:18], byte_order)

    def _has_codesign_section(self, objdump, path):
        section_table = self._run_tool(
            [objdump, "-h", path], f"inspect ELF sections in {path}"
        )
        return any(
            ".codesign" in line.split()
            for line in section_table.splitlines()
        )

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(f"Unable to {action}: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {detail or 'tool exited unsuccessfully'}"
            )
        return result.stdout

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        configured = os.environ.get(environment_variable)
        candidate = configured or executable
        resolved = shutil.which(candidate)
        if (
            not resolved
            and os.path.isfile(candidate)
            and os.access(candidate, os.X_OK)
        ):
            resolved = os.path.abspath(candidate)
        if (
            not resolved
            or not os.path.isfile(resolved)
            or not os.access(resolved, os.X_OK)
        ):
            raise ConanInvalidConfiguration(
                f"Required tool {executable} was not found; set "
                f"{environment_variable} or add it to PATH"
            )
        return os.path.abspath(resolved)

    def package_info(self):
        self.cpp_info.libs = ["Qt6HttpServer"]
        # The package installs Qt's own Qt6HttpServerConfig.cmake.  Consumers
        # should use it together with qtbase-gui's native Qt6Config.cmake.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.requires = [
            "qtbase-gui::core",
            "qtbase-gui::network",
        ]
        self.cpp_info.set_property("cmake_target_name", "Qt6::HttpServer")
