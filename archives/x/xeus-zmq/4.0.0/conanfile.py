#!/usr/bin/env python3
"""Conan recipe — xeus-zmq 4.0.0 (CMake, shared C++17 library).

xeus-zmq is the ZeroMQ-based backend for the xeus kernel framework.
It links xeus (PUBLIC), cppzmq + OpenSSL::Crypto (PRIVATE) and consumes
nlohmann_json.

W0 NOTE: this recipe requires ``xeus/[>=6.0,<7.0]`` which is NOT yet
adapted in this repository. xeus must be adapted and published in its own
separate PR before this package can be built. Do NOT fold xeus adaptation
into this PR.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class XeusZmqConan(ConanFile):
    name = "xeus-zmq"
    version = "4.0.0"
    description = "ZeroMQ-based backend for the xeus kernel framework"
    license = "BSD-3-Clause"
    homepage = "https://github.com/jupyter-xeus/xeus-zmq"
    url = "https://github.com/jupyter-xeus/xeus-zmq"

    package_type = "library"
    generators = "CMakeDeps"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tests": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "tests": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # xeus is exposed in the public headers (xzmq_context.hpp includes
        # xeus/xeus_context.hpp), so mark it as a public/interface requirement.
        self.requires("xeus/[>=6.0 <7.0]", transitive_headers=True, transitive_libs=True)
        self.requires("nlohmann_json/3.12.0", transitive_headers=True, transitive_libs=True)
        # cppzmq / zeromq / openssl are used only in the implementation (PRIVATE).
        self.requires("cppzmq/4.10.0")
        self.requires("zeromq/4.3.5")
        self.requires("openssl/3.0.16")
        # Upstream test suite (XEUS_ZMQ_BUILD_TESTS=ON) needs doctest at CMake
        # configure time (find_package(doctest REQUIRED)); enabled only when the
        # `tests` option is requested so the packaged build stays lean.
        if self.options.tests:
            self.requires("doctest/2.5.2")

    def validate(self):
        if self.settings.compiler.cppstd:
            check_min_cppstd(self, "17")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["XEUS_ZMQ_BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["XEUS_ZMQ_BUILD_STATIC_LIBS"] = "OFF" if self.options.shared else "ON"
        tc.variables["XEUS_ZMQ_STATIC_DEPENDENCIES"] = "OFF"
        # Upstream suite: with `tests=True` we build the real upstream test
        # binaries and execute the runnable upstream test(s) via ctest. The
        # packaged build (default) keeps tests OFF; consumer-level coverage is
        # provided by test_package.
        tc.variables["XEUS_ZMQ_BUILD_TESTS"] = "ON" if self.options.tests else "OFF"
        # zeromq in this repo was built WITHOUT CURVE/libsodium, so do not pull
        # libsodium here either.
        tc.variables["XEUS_ZMQ_BUILD_WITHOUT_LIBSODIUM"] = "ON"
        tc.generate()

        # The openssl recipe on ohpcd exports no CMake config files under the
        # conventional name, but xeus-zmq's CMakeLists requires
        # find_package(OpenSSL) + OpenSSL::Crypto. Since CMakeDeps also
        # generates openssl-config.cmake in this same folder, the shim simply
        # forwards to it (defines openssl::openssl + real include/lib paths)
        # and re-exposes the conventional OpenSSL::Crypto target name.
        version = str(self.ref.version) if hasattr(self.ref, "version") else "3.0.16"
        config_file = os.path.join(self.generators_folder, "OpenSSLConfig.cmake")
        with open(config_file, "w") as f:
            f.write("""# Auto-generated OpenSSLConfig.cmake (xeus-zmq consumer shim)
include("${{CMAKE_CURRENT_LIST_DIR}}/openssl-config.cmake")
set(OpenSSL_FOUND TRUE)
set(OPENSSL_FOUND TRUE)
set(OpenSSL_VERSION "{version}")
if(NOT TARGET OpenSSL::Crypto AND TARGET openssl::openssl)
    add_library(OpenSSL::Crypto INTERFACE IMPORTED)
    set_target_properties(OpenSSL::Crypto PROPERTIES
        INTERFACE_LINK_LIBRARIES openssl::openssl
    )
endif()
""".format(version=version))
        version_file = os.path.join(self.generators_folder, "OpenSSLConfigVersion.cmake")
        with open(version_file, "w") as f:
            f.write("""# Auto-generated OpenSSLConfigVersion.cmake
set(PACKAGE_VERSION "{version}")
if(PACKAGE_VERSION VERSION_LESS PACKAGE_FIND_VERSION)
    set(PACKAGE_VERSION_COMPATIBLE FALSE)
else()
    set(PACKAGE_VERSION_COMPATIBLE TRUE)
    if(PACKAGE_FIND_VERSION VERSION_EQUAL PACKAGE_VERSION)
        set(PACKAGE_VERSION_EXACT TRUE)
    endif()
endif()
""".format(version=version))

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.tests:
            # Real execution of the runnable upstream test(s) on the target:
            # - test_handshake is a self-contained C++ integration test
            #   (kernel handshake + kernel_info_request round-trip over ZMQ),
            #   runnable without a Python/Jupyter stack.
            # - test_kernel / test_kernel_control / test_kernel_shell are
            #   pytest drivers that need pytest + jupyter_client + pyzmq to
            #   spawn a live kernel; on the OHOS device none of these Python
            #   packages is available and pyzmq has no OHOS wheel (source build
            #   of the libzmq binding is out of scope), so they are excluded
            #   from the runnable set with -R.
            self.run("ctest --output-on-failure -R test_handshake", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if self.settings.os in ("Linux", "OHOS"):
            self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/storage/Users/currentUser/usr/local/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "xeus-zmq")
        self.cpp_info.set_property("cmake_target_name", "xeus-zmq")
        self.cpp_info.libs = ["xeus-zmq"]
        if not self.options.shared:
            self.cpp_info.defines = ["XEUS_ZMQ_STATIC_LIB"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
