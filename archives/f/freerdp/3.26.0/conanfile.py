#!/usr/bin/env python3
"""Conan recipe — freerdp 3.26.0 on HarmonyOS PC (OHOS / arm64).

FreeRDP is the free implementation of the Remote Desktop Protocol: the
portable WinPR layer (libwinpr3, libwinpr-tools3), the protocol core
(libfreerdp3, libfreerdp-client3) and the winpr command line tools
(winpr-makecert, winpr-hash).

Only the library half is built.  The front-ends (xfreerdp / sdl-freerdp /
wlfreerdp) need a windowing system (X11, Wayland or SDL2) plus a display
server, none of which the OHOS PC baseline ships, so WITH_CLIENT=OFF keeps
them out; WITH_CLIENT_COMMON=ON still builds libfreerdp-client3, which is the
library an embeddable RDP client links against.  The channel plugins (cliprdr,
rdpdr, rail, disp, rdpsnd, urbdrc, ...) are OBJECT libraries upstream, linked
into those front-ends and installed only through them (see the
add_channel_client_library macro in channels/CMakeLists.txt), so no plugin
artifact exists once the front-ends are off; WITH_CLIENT_CHANNELS=OFF states
that explicitly instead of compiling objects nothing links.

OHOS adaptations (each one verified against a local conan create):

  * soname -- CMAKE_SYSTEM_NAME=HarmonyOS has no CMake platform module, so
    CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG stays undefined and CMake then
    silently ignores upstream's own `set_target_properties(... VERSION ...
    SOVERSION ...)`.  Without the flag the four shared libraries are produced
    as libwinpr3.so with no DT_SONAME, and every consumer records the link
    path in DT_NEEDED (winpr/libwinpr/libwinpr3.so), which no loader can
    resolve; the repo L5a/L5b gates fail as well.  generate() supplies
    "-Wl,-soname," for C and C++, which brings upstream versioning back
    (libwinpr3.so.3.26.0 + libwinpr3.so.3 + libwinpr3.so symlinks).

  * OpenSSL -- CMakeDeps publishes a lowercase openssl-config.cmake and sets
    CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON, so upstream's find_package(OpenSSL)
    never reaches the bundled FindOpenSSL module.  winpr consumes the raw
    OPENSSL_FOUND / OPENSSL_INCLUDE_DIR / OPENSSL_LIBRARIES variables, which
    then stay empty.  generate() fills the three from the conan dependency.

  * libusb -- channels/urbdrc/CMakeLists.txt consumes LIBUSB_1_INCLUDE_DIRS /
    LIBUSB_1_LIBRARIES (module mode); the same PREFER_CONFIG redirect leaves
    both empty, so the urbdrc libusb subsystem compiles without its headers
    ("fatal error: 'libusb.h' file not found").  generate() passes both,
    exactly like upstream docs/mingw-example/Dockerfile does.

  * pthread_cancel -- musl has no pthread_cancel, but upstream only guarded
    the WinPR TerminateThread() call with `#ifndef ANDROID`.  patches/0001
    turns that into a `check_symbol_exists(pthread_cancel ...)` capability
    probe, so the shared libraries stop carrying an undefined symbol.

  * MD4 / RC4 -- NTLM (used by every RDP credential exchange) needs MD4, and
    the RDP standard security layer needs RC4.  OpenSSL 3 moved both into its
    legacy provider, which WinPR tries to load at runtime
    (winpr_openssl_initialize -> OSSL_PROVIDER_load(nullptr, "legacy")) but
    cannot find in a static OpenSSL package, so MD4 and RC4 simply fail
    ("OpenSSL LEGACY provider failed to load, no md4 support available").
    WITH_INTERNAL_MD4=ON and WITH_INTERNAL_RC4=ON switch WinPR to its own
    compiled-in implementations, exactly what upstream's android/windows/qa
    preload configs do (ci/cmake-preloads/config-qa.cmake,
    client/Android/cmake/ExternalFreeRDP.cmake).  Both are needed: MD4 alone
    still leaves winpr_RC4_New() failing.

  * ICU stays out of the dependency set: WITH_UNICODE_BUILTIN=ON uses the
    builtin Unicode tables.  FFMPEG / SWSCALE / CAIRO / CUPS / PCSC / KRB5 /
    GSSAPI / OPUS / ALSA / PULSE / SNDIO / OSS / FUSE / LIBSYSTEMD / PAM are
    off -- every one of them is optional upstream and none has headers in the
    OHOS baseline.

The upstream unit tests (BUILD_TESTING=ON, 157 ctest cases) link against the
build tree libs and need the build root as working directory; they are used
as a local verification step (see notes.md) and stay out of the package build.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class FreeRDPConan(ConanFile):
    name = "freerdp"
    version = "3.26.0"
    description = "FreeRDP - free implementation of the Remote Desktop Protocol (RDP)"
    license = "Apache-2.0"
    homepage = "https://www.freerdp.com/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("openssl/3.5.8.1")
        self.requires("zlib/1.3.2.1")
        self.requires("libusb/1.0.29")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ------------------------------------------------------------------ helpers
    def _static_or_shared_libs(self, dep):
        """Absolute link paths for a dependency, in the form the build verifies.

        Upstream links OpenSSL and libusb through plain CMake variables
        (OPENSSL_LIBRARIES / LIBUSB_1_LIBRARIES) that end up verbatim in
        target_link_libraries(), so the absolute archive path is the form that
        is known to work on this toolchain.
        """
        libs = []
        for libdir in dep.cpp_info.libdirs:
            for lib in dep.cpp_info.libs:
                for suffix in (".so", ".a"):
                    candidate = os.path.join(dep.package_folder, libdir, f"lib{lib}{suffix}")
                    if os.path.exists(candidate):
                        libs.append(candidate)
                        break
        return libs

    def generate(self):
        openssl = self.dependencies["openssl"]
        libusb = self.dependencies["libusb"]

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = False

        # 见模块文档：HarmonyOS 无 Platform 模块，SOVERSION 不注入 soname 标志就失效
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        # 前端需要 X11/Wayland/SDL 与显示服务器，OHOS 基线不提供
        tc.variables["WITH_CLIENT"] = False
        tc.variables["WITH_CLIENT_COMMON"] = True
        tc.variables["WITH_X11"] = False
        tc.variables["WITH_WAYLAND"] = False

        # 服务端 / 代理 / 影子会话同样依赖显示或输入后端
        tc.variables["WITH_SERVER"] = False
        tc.variables["WITH_SHADOW"] = False
        tc.variables["WITH_PROXY"] = False
        tc.variables["WITH_PLATFORM_SERVER"] = False

        # 通道插件是 OBJECT 库，只被前端链接，前端不构建时没有任何产物
        tc.variables["WITH_CLIENT_CHANNELS"] = False
        tc.variables["WITH_CHANNELS"] = True

        # 可选多媒体/设备后端：OHOS 基线无对应开发包
        for feature in ("FFMPEG", "SWSCALE", "CAIRO", "CUPS", "PCSC", "KRB5", "GSSAPI",
                        "OPUS", "ALSA", "PULSE", "SNDIO", "OSS", "FUSE", "LIBSYSTEMD",
                        "PAM", "SAMPLE"):
            tc.variables[f"WITH_{feature}"] = False

        tc.variables["WITH_WINPR_TOOLS"] = True
        # OpenSSL 3 把 MD4/RC4 移入 legacy provider，WinPR 加载不到 -> NTLM 与标准安全层不可用
        tc.variables["WITH_INTERNAL_MD4"] = True
        tc.variables["WITH_INTERNAL_RC4"] = True
        # 内置 Unicode 表，避免对 icu 的硬依赖（timezone ICU 默认已关）
        tc.variables["WITH_UNICODE_BUILTIN"] = True

        # 见模块文档：CMakeDeps 的 PREFER_CONFIG 让上游 module 模式变量落空
        tc.cache_variables["OPENSSL_FOUND"] = True
        tc.cache_variables["OPENSSL_INCLUDE_DIR"] = os.path.join(openssl.package_folder, "include")
        tc.cache_variables["OPENSSL_LIBRARIES"] = ";".join(self._static_or_shared_libs(openssl))
        tc.cache_variables["LIBUSB_1_INCLUDE_DIRS"] = os.path.join(
            libusb.package_folder, "include", "libusb-1.0")
        tc.cache_variables["LIBUSB_1_LIBRARIES"] = ";".join(self._static_or_shared_libs(libusb))

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["freerdp3", "freerdp-client3", "winpr3", "winpr-tools3"]
        self.cpp_info.includedirs = ["include/freerdp3", "include/winpr3"]
        self.cpp_info.bindirs = ["bin"]
