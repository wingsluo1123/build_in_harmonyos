#!/usr/bin/env python3
"""Conan recipe for KDSoap WS-Discovery Client 0.4.0 on HarmonyOS PC."""

import hashlib
import os
import platform
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, unzip


class KDSoapWSDiscoveryClientConan(ConanFile):
    name = "kdsoap-ws-discovery-client"
    version = "0.4.0"
    description = "Qt client library for the WS-Discovery protocol"
    license = "GPL-3.0-or-later"
    homepage = "https://invent.kde.org/libraries/kdsoap-ws-discovery-client"
    url = "https://invent.kde.org/libraries/kdsoap-ws-discovery-client"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("kdsoap/2.3.0")

    def build_requirements(self):
        self.tool_requires("extra-cmake-modules/6.29.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        local_archive = os.environ.get("KDSOAP_WSDISCOVERY_SOURCE_ARCHIVE")
        if local_archive:
            with open(local_archive, "rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual.lower() != source["sha256"].lower():
                raise ConanException("KDSoap WS-Discovery Client source archive SHA-256 mismatch")
            unzip(self, local_archive, destination=self.source_folder, strip_root=True)
        else:
            get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()

        qtbase = self.dependencies["qtbase"]
        kdsoap = self.dependencies["kdsoap"]
        ecm = self.dependencies.build["extra-cmake-modules"]
        qt_cmake = os.path.join(qtbase.package_folder, "lib", "cmake")
        ecm_share = os.path.join(ecm.package_folder, "share", "ECM")

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["QT_MAJOR_VERSION"] = "6"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["CMAKE_SKIP_RPATH"] = "ON"
        tc.variables["KDE_INSTALL_LIBDIR"] = "lib"
        tc.variables["KDE_INSTALL_CMAKEPACKAGEDIR"] = "lib/cmake"
        tc.cache_variables["ECM_DIR"] = os.path.join(ecm_share, "cmake")
        tc.variables["ECM_MODULE_PATH"] = ";".join(
            os.path.join(ecm_share, directory)
            for directory in ("modules", "find-modules", "kde-modules")
        )
        tc.cache_variables["KDSoap-qt6_DIR"] = os.path.join(
            kdsoap.package_folder, "lib", "cmake", "KDSoap-qt6"
        )
        for component in ("Qt6", "Qt6Core", "Qt6CoreTools", "Qt6Network", "Qt6Xml", "Qt6Test"):
            tc.cache_variables[f"{component}_DIR"] = os.path.join(qt_cmake, component)
        tc.generate()

    def _runtime_env(self):
        env = Environment()
        for dependency in ("qtbase", "kdsoap"):
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.dependencies[dependency].package_folder, "lib"))
        # KDECMakeSettings places executables and shared libraries under bin/.
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "bin"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "lib"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def build(self):
        cmake = CMake(self)
        with self._runtime_env().vars(self).apply():
            cmake.configure()
            cmake.build(build_tool_args=["-j1"])
            if can_run(self) and platform.system() == "HarmonyOS":
                self.run(
                    'ctest --test-dir "{}" --output-on-failure --no-tests=error --timeout 60 -j1'.format(
                        self.build_folder
                    )
                )

    def package(self):
        CMake(self).install()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_shared_libraries()

    def _sign_installed_shared_libraries(self):
        signer = shutil.which("binary-sign-tool")
        if not signer:
            raise ConanException("binary-sign-tool is required to sign installed OHOS shared libraries")
        for root, _, files in os.walk(self.package_folder):
            for name in files:
                binary = os.path.join(root, name)
                if os.path.islink(binary):
                    continue
                with open(binary, "rb") as stream:
                    header = stream.read(18)
                if len(header) < 18 or header[:4] != b"\x7fELF":
                    continue
                byte_order = {1: "little", 2: "big"}.get(header[5])
                if not byte_order or int.from_bytes(header[16:18], byte_order) not in (2, 3):
                    continue
                mode = stat.S_IMODE(os.stat(binary).st_mode)
                with tempfile.TemporaryDirectory(prefix=".wsd-sign-", dir=root) as temp:
                    signed = os.path.join(temp, "signed")
                    result = subprocess.run(
                        [signer, "sign", "-inFile", binary, "-outFile", signed, "-selfSign", "1"],
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    if result.returncode or not os.path.isfile(signed):
                        raise ConanException("Signing {} failed: {}".format(binary, result.stderr or result.stdout))
                    with open(signed, "rb") as stream:
                        if stream.read(4) != b"\x7fELF":
                            raise ConanException("Signing {} produced a non-ELF file".format(binary))
                    os.replace(signed, binary)
                    os.chmod(binary, mode | 0o755)

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("cmake_file_name", "KDSoapWSDiscoveryClient")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KDSoapWSDiscoveryClient"]
        self.cpp_info.requires = ["qtbase::core", "kdsoap::kdsoap"]
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
