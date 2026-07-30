#!/usr/bin/env python3
"""Conan recipe - GDAL 3.9.2 (cmake).

First-pass MapServer dependency build: keep the GDAL/OGR core, the command line
apps, PROJ coordinate support, SQLite/GPKG, and common raster codecs, while
disabling heavyweight optional stacks such as Curl, Arrow/Parquet, GEOS, WebP,
database backends, Python bindings, and upstream tests.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, get
from conan.tools.cmake import cmake_layout


class GdalConan(ConanFile):
    name = "gdal"
    version = "3.9.2"
    description = "GDAL/OGR geospatial raster and vector data abstraction library"
    license = "MIT"
    homepage = "https://gdal.org/"
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

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("proj/9.3.1")
        self.requires("sqlite3/3.49.1")
        self.requires("libtiff/4.7.2")
        self.requires("libpng/1.6.58")
        self.requires("libjpeg-turbo/3.2.0")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def _ohos_toolchain(self):
        user_toolchains = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(user_toolchains)
        if ndk:
            candidates.append(os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake"))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        globbed = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "Cannot find ohos.toolchain.cmake. Set OHOS_NDK_HOME or profile "
            "tools.cmake.cmaketoolchain:user_toolchain."
        )

    def _library(self, dep_name, names):
        libdir = os.path.join(self.dependencies[dep_name].package_folder, "lib")
        for name in names:
            hit = glob.glob(os.path.join(libdir, name))
            if hit:
                return hit[0]
        return os.path.join(libdir, names[0])

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        build_dir = os.path.join(self.build_folder, "build-ohos")

        proj = self.dependencies["proj"].package_folder
        sqlite = self.dependencies["sqlite3"].package_folder
        tiff = self.dependencies["libtiff"].package_folder
        png = self.dependencies["libpng"].package_folder
        jpeg = self.dependencies["libjpeg-turbo"].package_folder
        sqlite_lib = self._library("sqlite3", ["libsqlite3.a", "libsqlite3.so"])
        tiff_lib = self._library("libtiff", ["libtiff.so", "libtiff.a"])
        png_lib = self._library("libpng", ["libpng16.so", "libpng16.a", "libpng.so"])
        jpeg_lib = self._library("libjpeg-turbo", ["libjpeg.so", "libjpeg.a"])

        libdirs = [os.path.join(dep.package_folder, "lib") for dep in self.dependencies.values()]
        os.environ["LDFLAGS"] = " ".join(
            "-L{0} -Wl,-rpath-link,{0}".format(path) for path in libdirs
        ) + " " + os.environ.get("LDFLAGS", "")

        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DBUILD_SHARED_LIBS={}".format("ON" if self.options.shared else "OFF"),
            "-DBUILD_APPS=ON",
            "-DBUILD_TESTING=OFF",
            "-DBUILD_PYTHON_BINDINGS=OFF",
            "-DBUILD_DOCS=OFF",
            "-DGDAL_BUILD_OPTIONAL_DRIVERS=OFF",
            "-DOGR_BUILD_OPTIONAL_DRIVERS=OFF",
            "-DGDAL_ENABLE_PLUGINS=OFF",
            "-DGDAL_AUTOLOAD_PLUGINS=OFF",
            "-DGDAL_USE_INTERNAL_LIBS=WHEN_NO_EXTERNAL",
            "-DGDAL_USE_EXTERNAL_LIBS=OFF",
            "-DGDAL_USE_PROJ=ON",
            "-DGDAL_FIND_PACKAGE_PROJ_MODE=CONFIG",
            '-DPROJ_DIR="{}"'.format(os.path.join(proj, "lib", "cmake", "proj")),
            "-DGDAL_USE_SQLITE3=ON",
            '-DSQLite3_INCLUDE_DIR="{}"'.format(os.path.join(sqlite, "include")),
            '-DSQLite3_LIBRARY="{}"'.format(sqlite_lib),
            '-DSQLite3_LIBRARY_RELEASE="{}"'.format(sqlite_lib),
            "-DOGR_ENABLE_DRIVER_SQLITE=ON",
            "-DOGR_ENABLE_DRIVER_GPKG=ON",
            "-DGDAL_USE_TIFF=ON",
            '-DTIFF_INCLUDE_DIR="{}"'.format(os.path.join(tiff, "include")),
            '-DTIFF_LIBRARY="{}"'.format(tiff_lib),
            '-DTIFF_LIBRARY_RELEASE="{}"'.format(tiff_lib),
            "-DGDAL_USE_PNG=ON",
            '-DPNG_PNG_INCLUDE_DIR="{}"'.format(os.path.join(png, "include")),
            '-DPNG_LIBRARY="{}"'.format(png_lib),
            '-DPNG_LIBRARY_RELEASE="{}"'.format(png_lib),
            "-DGDAL_USE_JPEG=ON",
            '-DJPEG_INCLUDE_DIR="{}"'.format(os.path.join(jpeg, "include")),
            '-DJPEG_LIBRARY="{}"'.format(jpeg_lib),
            '-DJPEG_LIBRARY_RELEASE="{}"'.format(jpeg_lib),
            "-DGDAL_USE_CURL=OFF",
            "-DGDAL_USE_OPENSSL=OFF",
            "-DGDAL_USE_WEBP=OFF",
            "-DGDAL_USE_ARROW=OFF",
            "-DGDAL_USE_PARQUET=OFF",
            "-DGDAL_USE_ARROWDATASET=OFF",
            "-DGDAL_USE_ARROW_DATASET=OFF",
            "-DGDAL_USE_GEOS=OFF",
            "-DGDAL_USE_LIBXML2=OFF",
            "-DGDAL_USE_ICONV=OFF",
            "-DGDAL_USE_ZSTD=OFF",
            "-DGDAL_USE_LZMA=OFF",
            "-DGDAL_USE_LZ4=OFF",
            "-DGDAL_USE_EXPAT=OFF",
            "-DGDAL_USE_JSONC=OFF",
            "-DGDAL_USE_GIF=OFF",
            "-DGDAL_USE_QHULL=OFF",
            "-DGDAL_USE_PCRE2=OFF",
            "-DGDAL_USE_POSTGRESQL=OFF",
        ]
        self.run('cmake -B "{}" -S "{}" {}'.format(build_dir, self.source_folder, " ".join(defs)))
        self.run('cmake --build "{}"'.format(build_dir))

    def package(self):
        build_dir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(build_dir, self.package_folder))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        shared_libs = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        shared_libs += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not shared_libs:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for shared_lib in shared_libs:
            if os.path.islink(shared_lib):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=shared_lib))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=shared_lib))

    def package_info(self):
        self.cpp_info.libs = ["gdal"]
        self.cpp_info.set_property("cmake_file_name", "GDAL")
        self.cpp_info.set_property("cmake_target_name", "GDAL::GDAL")
        self.cpp_info.set_property("pkg_config_name", "gdal")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
