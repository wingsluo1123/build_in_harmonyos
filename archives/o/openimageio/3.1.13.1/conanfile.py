#!/usr/bin/env python3
"""Conan recipe for OpenImageIO 3.1.13.1.

OpenImageIO is a library for reading, writing, and manipulating images
of many formats. It provides the OIIO API, oiiotool, and various utilities.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class OpenImageIOConan(ConanFile):
    name = "openimageio"
    version = "3.1.13.1"
    description = "OpenImageIO — image I/O library with broad format support"
    license = "Apache-2.0"
    homepage = "https://github.com/AcademySoftwareFoundation/OpenImageIO"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("imath/3.2.2")
        self.requires("openexr/3.1.5")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libpng/1.6.58")
        self.requires("libtiff/4.7.2")
        self.requires("fmt/8.1.1")
        # libwebp disabled (USE_WEBP=OFF) - CMake target mismatch with Conan
        # self.requires("libwebp/1.6.0")
        self.requires("expat/2.8.2")
        self.requires("robin-map/1.4.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["USE_PYTHON"] = "OFF"
        tc.variables["USE_QT"] = "OFF"
        tc.variables["USE_OPENGL"] = "OFF"
        tc.variables["USE_FFMPEG"] = "OFF"
        tc.variables["USE_OPENCOLORIO"] = "OFF"
        tc.variables["USE_WEBP"] = "OFF"
        tc.variables["USE_FREETYPE"] = "OFF"
        tc.variables["USE_GIF"] = "OFF"
        tc.variables["USE_OPENCV"] = "OFF"
        tc.variables["USE_OPENJPEG"] = "OFF"
        tc.variables["USE_LIBHEIF"] = "OFF"
        tc.variables["USE_LIBRAW"] = "OFF"
        tc.variables["OIIO_INTERNALIZE_FMT"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["OpenImageIO_BUILD_MISSING_DEPS"] = "OFF"
        # Add fmt include directory to CMake flags since fmt::fmt-header-only
        # target doesn't exist in Conan CMakeDeps
        import os
        fmt_folder = self.dependencies["fmt"].package_folder
        tc.variables["CMAKE_C_FLAGS"] = f"-I{fmt_folder}/include"
        tc.variables["CMAKE_CXX_FLAGS"] = f"-I{fmt_folder}/include"
        # Add Imath include dirs for headers included without Imath/ prefix
        imath_folder = self.dependencies["imath"].package_folder
        tc.variables["CMAKE_C_FLAGS"] = f"-I{fmt_folder}/include -I{imath_folder}/include -I{imath_folder}/include/Imath"
        tc.variables["CMAKE_CXX_FLAGS"] = f"-I{fmt_folder}/include -I{imath_folder}/include -I{imath_folder}/include/Imath"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        import os
        # Fix: fmt/8.1.1 CMakeDeps version check only accepts same major (8.x),
        # but OpenImageIO requests fmt >= 7.0. Remove version constraint.
        ext_pkg = os.path.join(self.source_folder, "src", "cmake", "externalpackages.cmake")
        replace_in_file(self, ext_pkg, "VERSION_MIN 7.0\n                      BUILD_LOCAL missing", "")
        # Fix: OpenColorIO is disabled but CMake tries get_target_property on
        # non-existent OpenColorIO::OpenColorIO target. Add TARGET guard.
        replace_in_file(self, ext_pkg,
            "if (NOT OPENCOLORIO_INCLUDES)\n    get_target_property(OPENCOLORIO_INCLUDES OpenColorIO::OpenColorIO INTERFACE_INCLUDE_DIRECTORIES)\nendif ()",
            "if (TARGET OpenColorIO::OpenColorIO AND NOT OPENCOLORIO_INCLUDES)\n    get_target_property(OPENCOLORIO_INCLUDES OpenColorIO::OpenColorIO INTERFACE_INCLUDE_DIRECTORIES)\nendif ()")
        # Fix: fmt::fmt-header-only target doesn't exist in Conan CMakeDeps
        replace_in_file(self, ext_pkg,
            "get_target_property(FMT_INCLUDE_DIR fmt::fmt-header-only INTERFACE_INCLUDE_DIRECTORIES)",
            "if (TARGET fmt::fmt-header-only)\n    get_target_property(FMT_INCLUDE_DIR fmt::fmt-header-only INTERFACE_INCLUDE_DIRECTORIES)\nendif ()")
        # Fix: libutil/CMakeLists.txt links fmt::fmt-header-only which doesn't exist in CMakeDeps
        libutil_cmake = os.path.join(self.source_folder, "src", "libutil", "CMakeLists.txt")
        replace_in_file(self, libutil_cmake,
            "target_link_libraries (${targetname}\n                               PUBLIC fmt::fmt-header-only)",
            "target_link_libraries (${targetname}\n                               PUBLIC $<TARGET_NAME_IF_EXISTS:fmt::fmt-header-only>)")
        # Fix: libOpenImageIO/CMakeLists.txt links OpenColorIO::OpenColorIO directly
        # (other optional deps use $<TARGET_NAME_IF_EXISTS:...>, this one doesn't)
        oiio_cmake = os.path.join(self.source_folder, "src", "libOpenImageIO", "CMakeLists.txt")
        replace_in_file(self, oiio_cmake,
            "            OpenColorIO::OpenColorIO\n            $<TARGET_NAME_IF_EXISTS:OpenColorIO::OpenColorIOHeaders>",
            "            $<TARGET_NAME_IF_EXISTS:OpenColorIO::OpenColorIO>\n            $<TARGET_NAME_IF_EXISTS:OpenColorIO::OpenColorIOHeaders>")
        # Fix: color_ocio.cpp includes <OpenColorIO/OpenColorIO.h> but OpenColorIO is
        # disabled. Remove it from source lists to prevent compilation failure.
        replace_in_file(self, oiio_cmake, "color_ocio.cpp\n", "")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["OpenImageIO", "OpenImageIO_Util"]
        self.cpp_info.set_property("cmake_file_name", "OpenImageIO")
        self.cpp_info.set_property("cmake_target_name", "OpenImageIO::OpenImageIO")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl"]
