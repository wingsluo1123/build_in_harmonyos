#!/usr/bin/env python3
"""Conan recipe — sysdig 0.41.4 (CMake, two-phase with falcosecurity-libs).

Build sysdig 0.41.4 with pre-installed falcosecurity-libs 0.21.0.
E092: CMAKE_SYSTEM_NAME must be "Linux" (not OHOS) on HarmonyOS.
R32: settings.os must check `in ("Linux", "OHOS")`.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SysdigConan(ConanFile):
    name = "sysdig"
    version = "0.41.4"
    description = "System-level exploration and troubleshooting tool"
    license = "Apache-2.0"
    homepage = "https://github.com/draios/sysdig"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # System prefix where falcosecurity-libs and deps are installed
    _sys_prefix = os.path.expanduser("~/usr/local")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake doesn't recognize OHOS, use Linux
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["SYSDIG_VERSION"] = "0.41.4"
        tc.variables["USE_BUNDLED_DEPS"] = False
        tc.variables["BUILD_SYSDIG_MODERN_BPF"] = False
        # Point to pre-installed falcosecurity-libs
        tc.variables["CMAKE_PREFIX_PATH"] = self._sys_prefix
        # Mixed static/dynamic linking for OHOS musl compatibility
        syslib = self._sys_prefix + "/lib"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (
            f"-L{syslib} "
            "-Wl,-Bstatic -lsinsp -lscap -lscap_engine_nodriver "
            "-lscap_engine_source_plugin -lscap_engine_kmod -lscap_engine_bpf "
            "-lscap_event_schema -lscap_platform -lre2 -ljsoncpp -lluajit-5.1 "
            "-lelf -ldw -lz -lzstd -lbz2 -llzma -largp "
            "-Wl,-Bdynamic -ltbb -lncursesw -lpthread -lm -ldl"
        )
        tc.variables["CURSES_LIBRARY"] = f"{syslib}/libncursesw.so"
        tc.variables["CURSES_INCLUDE_PATH"] = f"{self._sys_prefix}/include"
        tc.generate()

        # Fix compiler paths if profile's paths don't exist locally (E001)
        cc = shutil.which("clang") or "clang"
        cxx = shutil.which("clang++") or "clang++"
        toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.exists(toolchain_file):
            with open(toolchain_file, "r") as f:
                content = f.read()
            content = re.sub(
                r'set\(CMAKE_C_COMPILER\s+"[^"]+"\)',
                f'set(CMAKE_C_COMPILER "{cc}")',
                content
            )
            content = re.sub(
                r'set\(CMAKE_CXX_COMPILER\s+"[^"]+"\)',
                f'set(CMAKE_CXX_COMPILER "{cxx}")',
                content
            )
            with open(toolchain_file, "w") as f:
                f.write(content)

    def build(self):
        apply_conandata_patches(self)
        # Set PKG_CONFIG_PATH so cmake can find libsinsp
        env = {
            "PKG_CONFIG_PATH": f"{self._sys_prefix}/lib/pkgconfig:{os.environ.get('PKG_CONFIG_PATH', '')}",
            "LD_LIBRARY_PATH": f"{self._sys_prefix}/lib:{os.environ.get('LD_LIBRARY_PATH', '')}",
        }
        with self._conan_helper_environment(env):
            cmake = CMake(self)
            cmake.configure()
            cmake.build(target="sysdig")

    def package(self):
        copy(self, "sysdig", src=os.path.join(self.build_folder, "userspace", "sysdig"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # sysdig is a CLI tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.system_libs = ["pthread", "m", "dl"]
        # Declare bindir so conanrun env includes it in PATH
        self.cpp_info.bindirs = ["bin"]

    def validate(self):
        # R32: settings.os must check both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def _conan_helper_environment(self, env_dict):
        """Context manager to temporarily set environment variables."""
        from contextlib import contextmanager
        @contextmanager
        def _ctx():
            old = {}
            for k, v in env_dict.items():
                old[k] = os.environ.get(k)
                os.environ[k] = v
            try:
                yield
            finally:
                for k, v in old.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
        return _ctx()
