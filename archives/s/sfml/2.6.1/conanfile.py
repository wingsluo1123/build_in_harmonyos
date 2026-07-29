#!/usr/bin/env python3
"""Conan recipe for SFML 2.6.1 System and Network modules."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, rmdir


class SfmlConan(ConanFile):
    name = "sfml"
    version = "2.6.1"
    description = "Simple and Fast Multimedia Library base modules"
    license = "Zlib"
    homepage = "https://www.sfml-dev.org/"
    url = "https://github.com/SFML/SFML"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["SFML_BUILD_AUDIO"] = False
        toolchain.variables["SFML_BUILD_WINDOW"] = False
        toolchain.variables["SFML_BUILD_GRAPHICS"] = False
        toolchain.variables["SFML_BUILD_NETWORK"] = True
        toolchain.variables["SFML_BUILD_EXAMPLES"] = False
        toolchain.variables["SFML_BUILD_TEST_SUITE"] = False
        toolchain.variables["SFML_BUILD_DOC"] = False
        toolchain.generate()

    def build(self):
        config_path = os.path.join(self.source_folder, "cmake", "Config.cmake")
        replace_in_file(
            self,
            config_path,
            'elseif(${CMAKE_SYSTEM_NAME} STREQUAL "Linux")',
            'elseif(${CMAKE_SYSTEM_NAME} STREQUAL "Linux" OR '
            '${CMAKE_SYSTEM_NAME} STREQUAL "OHOS")',
        )

        thread_path = os.path.join(
            self.source_folder, "src", "SFML", "System", "Unix", "ThreadImpl.cpp"
        )
        terminate_anchor = (
            "        #ifndef SFML_SYSTEM_ANDROID\n"
            "            pthread_cancel(m_thread);\n"
            "        #else\n"
            "            // See https://stackoverflow.com/questions/4610086/pthread-cancel-al\n"
            "            pthread_kill(m_thread, SIGUSR1);\n"
            "        #endif"
        )
        terminate_ohos = (
            "        #if defined(__OHOS__)\n"
            "            pthread_detach(m_thread);\n"
            "        #elif !defined(SFML_SYSTEM_ANDROID)\n"
            "            pthread_cancel(m_thread);\n"
            "        #else\n"
            "            // See https://stackoverflow.com/questions/4610086/pthread-cancel-al\n"
            "            pthread_kill(m_thread, SIGUSR1);\n"
            "        #endif"
        )
        replace_in_file(self, thread_path, terminate_anchor, terminate_ohos)
        replace_in_file(
            self,
            thread_path,
            "    #ifndef SFML_SYSTEM_ANDROID\n"
            "        // Tell the thread to handle cancel requests immediately\n"
            "        pthread_setcanceltype(PTHREAD_CANCEL_ASYNCHRONOUS, NULL);\n"
            "    #endif",
            "    #if !defined(SFML_SYSTEM_ANDROID) && !defined(__OHOS__)\n"
            "        // Tell the thread to handle cancel requests immediately\n"
            "        pthread_setcanceltype(PTHREAD_CANCEL_ASYNCHRONOUS, NULL);\n"
            "    #endif",
        )

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "license.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SFML")

        system = self.cpp_info.components["system"]
        system.libs = ["sfml-system"]
        system.set_property("cmake_target_name", "SFML::System")
        if self.settings.os in ("Linux", "OHOS"):
            system.system_libs = ["pthread"]

        network = self.cpp_info.components["network"]
        network.libs = ["sfml-network"]
        network.requires = ["system"]
        network.set_property("cmake_target_name", "SFML::Network")
