#!/usr/bin/env python3
"""Conan recipe for the Qt 6.11.1 GUI foundation on HarmonyOS PC."""

import glob
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class QtbaseGuiConan(ConanFile):
    name = "qtbase-gui"
    version = "6.11.1"
    description = "Qt Core, Network, Gui and Widgets modules for HarmonyOS PC"
    license = "BSD-3-Clause AND LGPL-3.0-only AND GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-6/qtbase-index.html"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _has_pthread_cancel(self):
        """Detect whether pthread cancellation APIs can be compiled and linked."""
        test_code = (
            "#include <pthread.h>\n"
            "int main(void) {\n"
            "    int old_state;\n"
            "    return pthread_setcancelstate(PTHREAD_CANCEL_DISABLE, "
            "&old_state);\n"
            "}\n"
        )
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c") or os.environ.get("CC") or "clang"
        with tempfile.NamedTemporaryFile(
            suffix=".c", mode="w", delete=False
        ) as source_file:
            source_file.write(test_code)
            source_file.flush()
            executable = source_file.name + ".out"
            try:
                result = subprocess.run(
                    [compiler, source_file.name, "-o", executable],
                    capture_output=True,
                    timeout=30,
                )
                return result.returncode == 0
            except (OSError, subprocess.SubprocessError):
                return False
            finally:
                os.unlink(source_file.name)
                if os.path.exists(executable):
                    os.unlink(executable)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables.update(
            {
                "QT_QMAKE_TARGET_MKSPEC": "harmonyos-clang",
                "BUILD_SHARED_LIBS": "ON" if self.options.shared else "OFF",
                "QT_BUILD_TESTS": "OFF",
                "QT_BUILD_TESTS_BY_DEFAULT": "OFF",
                "QT_BUILD_EXAMPLES": "OFF",
                "QT_BUILD_EXAMPLES_BY_DEFAULT": "OFF",
                "FEATURE_gui": "ON",
                "FEATURE_network": "ON",
                "FEATURE_widgets": "ON",
                "FEATURE_graphicsview": "ON",
                "FEATURE_xml": "ON",
                "FEATURE_printsupport": "OFF",
                "FEATURE_sql": "OFF",
                "FEATURE_testlib": "OFF",
                "FEATURE_dbus": "OFF",
                "FEATURE_openssl": "OFF",
                "FEATURE_opengl": "OFF",
                "FEATURE_opengles2": "OFF",
                "FEATURE_egl": "OFF",
                "FEATURE_eglfs": "OFF",
                "FEATURE_vulkan": "OFF",
                "FEATURE_xcb": "OFF",
                "FEATURE_xlib": "OFF",
                "FEATURE_linuxfb": "OFF",
                "FEATURE_vnc": "OFF",
                "FEATURE_evdev": "OFF",
                "FEATURE_libinput": "OFF",
                "FEATURE_mtdev": "OFF",
                "FEATURE_tslib": "OFF",
                "FEATURE_fontconfig": "OFF",
                "FEATURE_gtk3": "OFF",
                "FEATURE_accessibility_atspi_bridge": "OFF",
                "FEATURE_libudev": "OFF",
                "FEATURE_icu": "OFF",
                "FEATURE_pkg_config": "OFF",
                "FEATURE_system_zlib": "OFF",
                "FEATURE_system_pcre2": "OFF",
                "FEATURE_freetype": "ON",
                "FEATURE_system_freetype": "OFF",
                "FEATURE_harfbuzz": "ON",
                "FEATURE_system_harfbuzz": "OFF",
                "FEATURE_png": "ON",
                "FEATURE_system_png": "OFF",
                "FEATURE_jpeg": "ON",
                "FEATURE_system_jpeg": "OFF",
            }
        )

        # Append target-specific options instead of assigning
        # CMAKE_CXX_FLAGS, which would discard flags supplied by the
        # Conan profile, environment and compiler wrapper.
        if str(self.settings.arch) == "armv8":
            tc.extra_cxxflags.append("-march=armv8-a+crypto")
        if not self._has_pthread_cancel():
            tc.extra_cxxflags.append("-DQT_NO_PTHREAD_CANCEL")
            self.output.info(
                "pthread cancellation APIs unavailable; "
                "defining QT_NO_PTHREAD_CANCEL"
            )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        """Re-sign installed OHOS shared objects after CMake edits RPATHs."""
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        patterns = ("*.so", "*.so.*")
        libraries = []
        for pattern in patterns:
            libraries.extend(
                glob.glob(
                    os.path.join(self.package_folder, "lib", "**", pattern),
                    recursive=True,
                )
            )
        for library in sorted(set(libraries)):
            if os.path.islink(library):
                continue
            self.run(f'"{objcopy}" --remove-section .codesign "{library}"')
            self.run(
                f'"{signer}" sign -inFile "{library}" '
                f'-outFile "{library}" -selfSign 1'
            )

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        configured = os.environ.get(environment_variable)
        resolved = configured or shutil.which(executable)
        if not resolved or not os.path.isfile(resolved):
            raise ConanInvalidConfiguration(
                f"Required tool {executable} was not found; set "
                f"{environment_variable} or add it to PATH"
            )
        return os.path.abspath(resolved)

    def package_info(self):
        # Qt installs complete, relocatable Qt6Config.cmake files. Prevent
        # CMakeDeps from shadowing them with an incomplete generated config.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]

        core = self.cpp_info.components["core"]
        core.libs = ["Qt6Core"]
        core.set_property("cmake_target_name", "Qt6::Core")

        network = self.cpp_info.components["network"]
        network.libs = ["Qt6Network"]
        network.requires = ["core"]
        network.set_property("cmake_target_name", "Qt6::Network")

        gui = self.cpp_info.components["gui"]
        gui.libs = ["Qt6Gui"]
        gui.requires = ["core"]
        gui.set_property("cmake_target_name", "Qt6::Gui")

        widgets = self.cpp_info.components["widgets"]
        widgets.libs = ["Qt6Widgets"]
        widgets.requires = ["core", "gui"]
        widgets.set_property("cmake_target_name", "Qt6::Widgets")

        xml = self.cpp_info.components["xml"]
        xml.libs = ["Qt6Xml"]
        xml.requires = ["core"]
        xml.set_property("cmake_target_name", "Qt6::Xml")
