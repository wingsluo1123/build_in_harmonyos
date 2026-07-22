#!/usr/bin/env python3
"""Conan recipe for SDL3 3.4.8 on OpenHarmony PC (aarch64, bionic libc).

SDL3 is not a system same-name library (no OHOS libSDL3.so in /lib) so we
default to **static** linking per the project's R26 policy applied
broadly to keep downstream consumer packaging simple (one .a per dep).

OHOS specifics:
- CMake `CMAKE_SYSTEM_NAME=HarmonyOS` is auto-mapped from Conan `os=OHOS`.
- Patches add a `SDL_PLATFORM_OHOS` define and OHOS-aware build-system
  branches so SDL3's unix core can drive the linux framebuffer/dummy
  drivers without trying to link ALSA/PulseAudio/X11/Wayland.
- We forcibly disable every audio/video backend that needs server-side
  infra OHOS doesn't provide.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Sdl3Conan(ConanFile):
    name = "sdl3"
    version = "3.4.8"
    description = ("Simple DirectMedia Layer is a cross-platform multimedia "
                   "library designed to provide low level access to audio, "
                   "keyboard, mouse, joystick, 3D hardware via OpenGL, and "
                   "2D video framebuffer.")
    license = "Zlib"
    homepage = "https://libsdl.org/"
    url = "https://github.com/libsdl-org/SDL/releases/tag/release-3.4.8"
    topics = ("sdl", "multimedia", "graphics", "audio", "input")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # SDL3 ships its own libusb, hidapi, opus etc. internally for the
        # controllers subsystem; no external deps on OHOS.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Static-only (R26-style discipline for cross-compiled deps).
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # Threads: POSIX pthread backend is fine on bionic.
        tc.variables["SDL_PTHREADS"] = "ON"
        # Tray: no Gtk on OHOS — patches set this for us, but force anyway.
        tc.variables["SDL_TRAY"] = "OFF"
        # ─── Audio backends ────────────────────────────────────────────────
        # OHOS has no ALSA / PulseAudio / JACK / Pipewire / sndio.
        # SDL_OSS uses raw /dev/dsp which is also not on OHOS.
        # Fall back to the built-in "dummy" audio driver (always compiled).
        tc.variables["SDL_ALSA"] = "OFF"
        tc.variables["SDL_JACK"] = "OFF"
        tc.variables["SDL_PIPEWIRE"] = "OFF"
        tc.variables["SDL_PULSEAUDIO"] = "OFF"
        tc.variables["SDL_SNDIO"] = "OFF"
        tc.variables["SDL_OSS"] = "OFF"
        # ─── Video backends ────────────────────────────────────────────────
        # No X11 / Wayland / KMSDRM / DirectFB on OHOS. The "offscreen"
        # and "dummy" drivers are always built and allow headless tests.
        tc.variables["SDL_X11"] = "OFF"
        tc.variables["SDL_WAYLAND"] = "OFF"
        tc.variables["SDL_KMSDRM"] = "OFF"
        tc.variables["SDL_DIRECTFB"] = "OFF"
        tc.variables["SDL_RPI"] = "OFF"
        tc.variables["SDL_ROCKCHIP"] = "OFF"
        tc.variables["SDL_VIVANTE"] = "OFF"
        tc.variables["SDL_OPENVR"] = "OFF"
        # 3D rendering: no GL/GLES surface on OHOS headless tests.
        tc.variables["SDL_OPENGL"] = "OFF"
        tc.variables["SDL_OPENGLES"] = "OFF"
        # ─── Misc ──────────────────────────────────────────────────────────
        tc.variables["SDL_DBUS"] = "OFF"
        tc.variables["SDL_IBUS"] = "OFF"
        tc.variables["SDL_LIBUDEV"] = "OFF"
        tc.variables["SDL_ASAN"] = "OFF"
        # Output: we only need the static archive.
        tc.variables["SDL_SHARED"] = "OFF"
        tc.variables["SDL_STATIC"] = "ON"
        # Tests: SDL3's bundled test/ tree has dozens of drivers and
        # depends on X11/Wayland. Skip them; our test_package covers R34.
        tc.variables["SDL_TESTS"] = "OFF"
        tc.variables["SDL_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Strip non-portable CMake package config from the install tree;
        # we want downstream to use our package_info() only.
        # (SDL's installed SDL3Config.cmake assumes a system install layout
        # and points at /usr/lib etc. which OHOS doesn't have.)
        # Keep headers, libSDL3.a, and license.

    def package_info(self):
        self.cpp_info.libs = ["SDL3"]
        # SDL3 uses math functions but doesn't link libm itself — let the
        # consumer bring it in (matches upstream behavior).
        # system_libs: pthread is required for SDL_CreateThread etc.
        self.cpp_info.system_libs = ["pthread"]

    def package_id(self):
        # Bionic libc++ ABI is consistent across OHOS profiles; no need
        # to vary per compiler.libcxx.
        del self.info.settings.compiler.libcxx