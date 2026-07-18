#!/usr/bin/env python3
"""Conan recipe for baresip 4.9.0 — CMake build system.

baresip is a modular SIP user-agent with audio/video support.
Build system: CMake

Key rules:
  - R9:  Use make -j1 (not -j$(nproc))
  - R32: settings.os check uses `in ("Linux", "OHOS")`
  - re (libre) is used from system installation at /storage/Users/currentUser/usr/local
  - Do NOT set CMAKE_SYSTEM_NAME=Linux (avoids Linux-only source files that
    cause sockaddr_storage redefinition on OHOS)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class BaresipConan(ConanFile):
    name = "baresip"
    version = "4.9.0"
    description = "Modular SIP user-agent with audio/video support"
    license = "BSD"
    homepage = "https://github.com/baresip/baresip"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Patch FindRE.cmake to search in the custom prefix for re headers
        # Without CMAKE_SYSTEM_NAME=Linux, CMake doesn't recognize OHOS as UNIX,
        # so FindRE.cmake's hardcoded /usr/local paths won't be searched.
        findre_path = os.path.join(self.source_folder, "cmake", "FindRE.cmake")
        if os.path.exists(findre_path):
            with open(findre_path, "r") as f:
                content = f.read()
            old = "PATHS /usr/local/include/re /usr/include/re"
            new = "PATHS /storage/Users/currentUser/usr/local/include/re /usr/local/include/re /usr/include/re"
            if old in content:
                content = content.replace(old, new)
                with open(findre_path, "w") as f:
                    f.write(content)
            # Also add the re library search path
            old2 = "PATHS /usr/local/lib64 /usr/lib64 /usr/local/lib /usr/lib"
            new2 = "PATHS /storage/Users/currentUser/usr/local/lib /usr/local/lib64 /usr/lib64 /usr/local/lib /usr/lib"
            if old2 in content:
                content = content.replace(old2, new2)
                with open(findre_path, "w") as f:
                    f.write(content)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")
        # Do NOT set CMAKE_SYSTEM_NAME=Linux — that would pull in Linux-specific
        # source files (src/net/linux/rt.c) that cause sockaddr_storage redefinition
        tc.variables["STATIC"] = "OFF"
        tc.variables["CMAKE_PREFIX_PATH"] = "/storage/Users/currentUser/usr/local"
        # Exclude modules that have OHOS compatibility issues:
        # - sndfile: triggers CMake FindPkgConfig bug on OHOS
        # - netroam: sockaddr_storage redefinition from linux/netlink.h
        # - aac/opus/pulse/alsa/portaudio: missing system audio libs
        # - directfb/gtk/sdl/v4l2/x11: missing display/graphics libs
        # - coreaudio/audiounit/dshow/wasapi: macOS/Windows only
        tc.variables["MODULES"] = (
            "account;aubridge;auconv;aufile;augain;auresamp;ausine;cons;contact;"
            "ctrl_tcp;debug_cmd;dtls_srtp;echo;fakevideo;g711;httpd;httpreq;ice;"
            "in_band_dtmf;l16;menu;mixausrc;mixminus;mwi;pcp;"
            "presence;rtcpsummary;selfview;serreg;srtp;stdio;stun;syslog;turn;"
            "uuid;vidbridge;vidinfo;vumeter"
        )
        # Pre-set RE_INCLUDE_DIRS for the baresip CMakeLists.txt
        tc.variables["RE_INCLUDE_DIR"] = "/storage/Users/currentUser/usr/local/include/re"
        tc.variables["RE_INCLUDE_DIRS"] = "/storage/Users/currentUser/usr/local/include/re"
        tc.variables["RE_LIBRARY"] = "/storage/Users/currentUser/usr/local/lib/libre.a"
        tc.variables["RE_LIBRARIES"] = "/storage/Users/currentUser/usr/local/lib/libre.a"
        # Explicitly set OpenSSL paths for the linker to find SSL symbols
        tc.variables["OPENSSL_INCLUDE_DIR"] = "/storage/Users/currentUser/usr/local/include"
        tc.variables["OPENSSL_ROOT_DIR"] = "/storage/Users/currentUser/usr/local"
        tc.variables["OPENSSL_SSL_LIBRARY"] = "/storage/Users/currentUser/usr/local/lib/libssl.so"
        tc.variables["OPENSSL_CRYPTO_LIBRARY"] = "/storage/Users/currentUser/usr/local/lib/libcrypto.so"
        # Add OpenSSL libs to linker flags so selftest can resolve symbols
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-L/storage/Users/currentUser/usr/local/lib -lssl -lcrypto"
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-L/storage/Users/currentUser/usr/local/lib -lssl -lcrypto"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder=self.source_folder)
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["baresip"]
        self.cpp_info.bindirs = ["bin"]