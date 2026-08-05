#!/usr/bin/env python3
"""Conan recipe -- libgd 2.3.3 (GD graphics library, CMake).

libgd is a graphics library for dynamically creating images.
It supports PNG, JPEG, GIF, WBMP, and BMP formats, plus
Freetype text rendering.

Homepage: https://libgd.github.io/
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    get,
    copy,
    apply_conandata_patches,
    export_conandata_patches,
    save,
)


class LibgdConan(ConanFile):
    name = "libgd"
    version = "2.3.3"
    description = "GD graphics library -- image creation and manipulation"
    license = "gd"
    homepage = "https://libgd.github.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libgd supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libpng/1.6.58")
        self.requires("libjpeg/10")
        self.requires("freetype/2.14.3")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---- helpers ----

    def _dep_pkg(self, name):
        return self.dependencies[name].package_folder

    def _dep_incdir(self, name):
        return os.path.join(self._dep_pkg(name), "include").replace("\\", "/")

    def _dep_lib(self, name, candidates):
        """Find the actual library file in the dependency lib directory."""
        pkg = self._dep_pkg(name)
        for cand in candidates:
            matches = sorted(glob.glob(os.path.join(pkg, "lib", cand)))
            if matches:
                return matches[0].replace("\\", "/")
        return os.path.join(pkg, "lib", candidates[0]).replace("\\", "/")

    def generate(self):
        tc = CMakeToolchain(self)

        # --- OHOS: emit proper SONAME / RPATH for shared libs ---
        if self.settings.os == "OHOS":
            rules = os.path.join(self.generators_folder, "ohos-cmake-rules.cmake")
            save(
                self,
                rules,
                "\n".join(
                    (
                        'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                        'set(CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG '
                        '"-Wl,-rpath-link,")',
                        'set(CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN "$ORIGIN")',
                    )
                )
                + "\n",
            )
            tc.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules

        # --- enable the formats we have conan deps for ---
        tc.cache_variables["ENABLE_PNG"] = True
        tc.cache_variables["ENABLE_JPEG"] = True
        tc.cache_variables["ENABLE_FREETYPE"] = True
        tc.cache_variables["ENABLE_GD_FORMATS"] = True
        tc.cache_variables["ENABLE_CPP"] = False  # C-only build

        # --- disable formats we have no conan deps for ---
        for opt in (
            "ENABLE_TIFF", "ENABLE_ICONV", "ENABLE_XPM",
            "ENABLE_FONTCONFIG", "ENABLE_WEBP", "ENABLE_HEIF",
            "ENABLE_AVIF", "ENABLE_LIQ", "ENABLE_RAQM",
        ):
            tc.cache_variables[opt] = False

        # --- shared/static ---
        shared = bool(self.options.shared)
        tc.cache_variables["BUILD_SHARED_LIBS"] = shared
        tc.cache_variables["BUILD_STATIC_LIBS"] = not shared

        # --- wire conan deps into CMake built-in Find* modules ---
        # libgd uses CMake's built-in find_package(ZLIB/PNG/JPEG/Freetype).
        # We pre-set the cache variables so the find modules don't search.

        # ZLIB
        z_lib = self._dep_lib("zlib", ["libz.a", "libz.so"])
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = self._dep_incdir("zlib")
        tc.cache_variables["ZLIB_LIBRARY"] = z_lib
        tc.cache_variables["ZLIB_LIBRARY_RELEASE"] = z_lib

        # PNG (libpng provides libpng16.so)
        png_lib = self._dep_lib("libpng", ["libpng16.so", "libpng.so",
                                          "libpng16.a", "libpng.a"])
        png_inc = self._dep_incdir("libpng")
        tc.cache_variables["PNG_PNG_INCLUDE_DIR"] = png_inc
        tc.cache_variables["PNG_INCLUDE_DIR"] = png_inc
        tc.cache_variables["PNG_LIBRARY"] = png_lib
        tc.cache_variables["PNG_LIBRARY_RELEASE"] = png_lib

        # JPEG (libjpeg defaults to static: libjpeg.a)
        jpeg_lib = self._dep_lib("libjpeg", ["libjpeg.a", "libjpeg.so"])
        tc.cache_variables["JPEG_INCLUDE_DIR"] = self._dep_incdir("libjpeg")
        tc.cache_variables["JPEG_LIBRARY"] = jpeg_lib
        tc.cache_variables["JPEG_LIBRARY_RELEASE"] = jpeg_lib

        # Freetype (headers in include/freetype2/, lib = libfreetype.so)
        ft_pkg = self._dep_pkg("freetype")
        ft_inc = os.path.join(ft_pkg, "include", "freetype2").replace("\\", "/")
        ft_lib = self._dep_lib("freetype", ["libfreetype.so", "libfreetype.a"])
        tc.cache_variables["FREETYPE_INCLUDE_DIR_ft2build"] = ft_inc
        tc.cache_variables["FREETYPE_INCLUDE_DIR_freetype2"] = ft_inc
        tc.cache_variables["FREETYPE_LIBRARY"] = ft_lib
        tc.cache_variables["FREETYPE_LIBRARY_RELEASE"] = ft_lib

        # --- rpath-link for shared deps so the linker resolves them ---
        if shared:
            tc.cache_variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
            tc.cache_variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = False
            ld_dirs = []
            for dep in ("zlib", "libpng", "freetype"):
                ld_dirs.append(os.path.join(self._dep_pkg(dep), "lib"))
            existing = os.environ.get("LDFLAGS", "")
            os.environ["LDFLAGS"] = (
                " ".join(f"-L{d} -Wl,-rpath-link,{d}" for d in ld_dirs)
                + " "
                + existing
            )

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["gd"]
        self.cpp_info.set_property("cmake_file_name", "GD")
        self.cpp_info.set_property("cmake_target_name", "GD::GD")
        self.cpp_info.set_property("pkg_config_name", "gdlib")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
