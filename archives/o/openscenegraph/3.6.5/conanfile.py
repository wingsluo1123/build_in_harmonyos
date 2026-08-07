#!/usr/bin/env python3
"""Conan recipe for OpenSceneGraph 3.6.5 on HarmonyOS PC (aarch64).

OpenSceneGraph is a high-performance 3D graphics toolkit built on OpenGL ES 3.0.
This recipe builds OSG with GLES3/EGL backend (no X11 windowing system).
System libraries: EGL, GLESv3 (provided by HarmonyOS at /system/lib64/).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OpenscenegraphConan(ConanFile):
    name = "openscenegraph"
    version = "3.6.5"
    description = "High-performance 3D graphics toolkit for real-time visualization and simulation"
    license = "LGPL-2.1-with-WxWindows-exception"
    homepage = "https://github.com/openscenegraph/OpenSceneGraph"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    options = {
        "shared": [True, False],
        "with_jpeg": [True, False],
        "with_png": [True, False],
        "with_tiff": [True, False],
        "with_curl": [True, False],
        "with_fontconfig": [True, False],
    }
    default_options = {
        "shared": True,
        "with_jpeg": True,
        "with_png": True,
        "with_tiff": True,
        "with_curl": True,
        "with_fontconfig": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("freetype/2.14.3")
        if self.options.with_jpeg:
            self.requires("libjpeg-turbo/3.2.0")
        if self.options.with_png:
            self.requires("libpng/1.6.58")
        if self.options.with_tiff:
            self.requires("libtiff/4.7.2")
        if self.options.with_curl:
            self.requires("curl/8.15.0")
        if self.options.with_fontconfig:
            self.requires("fontconfig/2.18.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake policy compatibility (OSG 3.6.5 requires cmake >= 2.6)
        # Must use cache_variables so it's passed as -D on command line,
        # because cmake_minimum_required() is processed before toolchain file
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # GLES3/EGL backend (no desktop OpenGL, no X11)
        tc.variables["OPENGL_PROFILE"] = "GLES3"
        tc.variables["OSG_GLES3_AVAILABLE"] = "ON"
        tc.variables["OSG_GL1_AVAILABLE"] = "OFF"
        tc.variables["OSG_GL2_AVAILABLE"] = "OFF"
        tc.variables["OSG_GL3_AVAILABLE"] = "OFF"
        tc.variables["OSG_GLES1_AVAILABLE"] = "OFF"
        tc.variables["OSG_GLES2_AVAILABLE"] = "OFF"
        tc.variables["OSG_GL_FIXED_FUNCTION_AVAILABLE"] = "OFF"
        tc.variables["OSG_GL_DISPLAYLISTS_AVAILABLE"] = "OFF"
        tc.variables["OSG_GL_MATRICES_AVAILABLE"] = "OFF"
        tc.variables["OSG_GL_VERTEX_FUNCS_AVAILABLE"] = "OFF"
        tc.variables["OSG_GL_VERTEX_ARRAY_FUNCS_AVAILABLE"] = "OFF"
        # No windowing system (HarmonyOS has no X11)
        tc.variables["OSG_WINDOWING_SYSTEM"] = "None"
        # Disable unavailable optional dependencies
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_SDL2"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_X11"] = True
        # System EGL/GLES3 paths for HarmonyOS
        if self.settings.os in ("Linux", "OHOS"):
            sysroot = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot"
            if os.path.isdir(sysroot):
                tc.variables["OPENGL_INCLUDE_DIR"] = os.path.join(sysroot, "usr", "include")
                tc.variables["EGL_INCLUDE_DIR"] = os.path.join(sysroot, "usr", "include")
            tc.variables["OPENGL_gl_LIBRARY"] = "/system/lib64/libGLESv3.so"
            tc.variables["OPENGL_opengl_LIBRARY"] = "/system/lib64/libGLESv3.so"
            tc.variables["EGL_LIBRARY"] = "/system/lib64/libEGL.so"
        # Suppress 'register' keyword error in generated lexer files (C++17 removes register)
        tc.extra_cxxflags.append("-Wno-register")
        # Enable SONAME support: CMake doesn't recognize HarmonyOS as Linux,
        # so CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG is not set. Without it,
        # libraries have no SONAME and NEEDED entries use full paths.
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # Disable RPATH: musl libc (HarmonyOS) resolves DT_RPATH before LD_LIBRARY_PATH,
        # and OSG's relative RPATH (../../lib/) doesn't resolve correctly.
        # With RPATH disabled, conan's conanrun.sh LD_LIBRARY_PATH handles library resolution.
        tc.variables["CMAKE_SKIP_RPATH"] = True
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
        # Core libraries produced by OpenSceneGraph
        self.cpp_info.libs = [
            "OpenThreads",
            "osg",
            "osgAnimation",
            "osgDB",
            "osgFX",
            "osgGA",
            "osgManipulator",
            "osgParticle",
            "osgPresentation",
            "osgShadow",
            "osgSim",
            "osgTerrain",
            "osgText",
            "osgUI",
            "osgUtil",
            "osgViewer",
            "osgVolume",
            "osgWidget",
        ]
        # System graphics libraries on HarmonyOS
        self.cpp_info.system_libs = ["EGL", "GLESv3"]
