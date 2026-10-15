#!/usr/bin/env python3
"""Conan recipe for Qt MQTT 6.11.1 (CMake)."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class QtMqttConan(ConanFile):
    name = "qt6-mqtt"
    version = "6.11.1"
    description = "Qt MQTT client module (MQTT 3.1.1 and MQTT 5.0)"
    license = "GPL-3.0-only OR LGPL-3.0-only OR LicenseRef-Qt-Commercial"
    homepage = "https://doc.qt.io/qt-6/qtmqtt-index.html"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "qtbase/6.11.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("qt6-mqtt supports Linux and OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase"].package_folder
        tc.variables["Qt6_DIR"] = os.path.join(qtbase, "lib", "cmake", "Qt6")
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        # The OHOS CMake platform module does not define the SONAME flag, so
        # shared libs would ship without DT_SONAME and consumers would
        # record path-form DT_NEEDED (E537). Enable it at link time: the
        # upstream target has VERSION/SOVERSION, so lld then emits a real
        # soname (libQt6Mqtt.so.6) matching the qtbase sibling libraries.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        if self.settings.os == "OHOS":
            tc.variables["QT_QMAKE_TARGET_MKSPEC"] = "harmonyos-clang"
        tc.variables["QT_BUILD_TESTS"] = True
        tc.variables["QT_BUILD_TESTS_BY_DEFAULT"] = True
        tc.variables["QT_BUILD_EXAMPLES"] = False
        tc.variables["QT_BUILD_EXAMPLES_BY_DEFAULT"] = False
        tc.variables["QT_BUILD_BENCHMARKS"] = False
        tc.variables["QT_BUILD_MANUAL_TESTS"] = False
        tc.generate()
        VirtualRunEnv(self).generate()

    def _ctest_executable(self):
        for candidate in (
            shutil.which("ctest"),
            "/data/service/hnp/bin/ctest",
            "/data/service/hnp/cmake.org/cmake_4.1.2/bin/ctest",
        ):
            if (
                candidate
                and os.path.isfile(candidate)
                and os.access(candidate, os.X_OK)
            ):
                return candidate
        raise ConanInvalidConfiguration("ctest executable was not found")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self.output.info(
                "Running broker-free upstream Qt MQTT auto tests with "
                "the Conan runtime environment"
            )
            ctest = self._ctest_executable()
            # The module lib now carries SONAME libQt6Mqtt.so.6 (E537 fix)
            # and musl's loader ignores DT_RUNPATH, so the build-tree lib
            # dir must be on LD_LIBRARY_PATH for the in-tree test binaries.
            libdir = os.path.join(self.build_folder, "lib")
            self.run(
                f'export LD_LIBRARY_PATH="{libdir}:$LD_LIBRARY_PATH" && '
                f'"{ctest}" --test-dir "{self.build_folder}" '
                '-R "^(module_includes|'
                "tst_(qmqttcontrolpacket|qmqtttopicfilter|qmqtttopicname)"
                '_Tcp_4)$" '
                "--output-on-failure -j1",
                env="conanrun",
            )
        else:
            self.output.info(
                "Cross-building: upstream Qt MQTT tests require "
                "a runnable target"
            )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "LICENSES"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["Qt6Mqtt"]
        # Qt installs complete Qt6MqttConfig.cmake files. Reuse them so
        # consumers keep the upstream Qt6::Mqtt target and avoid a
        # generated CMakeDeps config that would search for qtbaseConfig.cmake.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
