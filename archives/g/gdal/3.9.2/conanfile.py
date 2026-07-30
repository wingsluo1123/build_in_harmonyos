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
from conan.tools.cmake import CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv


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

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualBuildEnv(self).generate()

    def _ohos_arch(self):
        arch = str(self.settings.arch)
        arch_map = {
            "armv8": "arm64-v8a",
            "armv7": "armeabi-v7a",
            "x86_64": "x86_64",
        }
        if arch not in arch_map:
            raise ConanInvalidConfiguration(f"Unsupported OHOS architecture: {arch}")
        return arch_map[arch]

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
        fallback = os.path.join(libdir, names[0])
        raise ConanInvalidConfiguration(
            f"Cannot find {dep_name} library. Tried {names}; fallback missing: {fallback}"
        )

    def build(self):
        apply_conandata_patches(self)
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
        linker_flags = " ".join(
            "-L{0} -Wl,-rpath-link,{0}".format(path) for path in libdirs
        )

        defs = [
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            '-DCMAKE_EXE_LINKER_FLAGS="{}"'.format(linker_flags),
            '-DCMAKE_SHARED_LINKER_FLAGS="{}"'.format(linker_flags),
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
        if self.settings.os == "OHOS":
            defs.insert(0, "-DOHOS_ARCH={}".format(self._ohos_arch()))
            defs.insert(0, '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(self._ohos_toolchain()))
        else:
            conan_toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
            if os.path.isfile(conan_toolchain):
                defs.insert(0, '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(conan_toolchain))
        self.run(
            'cmake -B "{}" -S "{}" {}'.format(build_dir, self.source_folder, " ".join(defs)),
            env="conanbuild",
        )
        self.run('cmake --build "{}"'.format(build_dir), env="conanbuild")

    def package(self):
        build_dir = os.path.join(self.build_folder, "build-ohos")
        self.run(
            'cmake --install "{}" --prefix "{}"'.format(build_dir, self.package_folder),
            env="conanbuild",
        )
        if self.options.shared and self.settings.os == "OHOS":
            self._sign_shared_libs()

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        shared_libs = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        shared_libs += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not shared_libs:
            return
        objcopy = self._ohos_tool("llvm_objcopy", "llvm-objcopy")
        signer = self._ohos_tool("binary_sign_tool", "binary-sign-tool")
        if not (objcopy and signer):
            self.output.warning("Skipping OHOS shared-library signing: signing tools not found")
            return
        for shared_lib in shared_libs:
            if os.path.islink(shared_lib):
                continue
            self.run('{oc} --remove-section .codesign "{f}"'.format(oc=objcopy, f=shared_lib))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=shared_lib))

    def _ohos_tool(self, conf_name, executable):
        configured = self.conf.get(f"user.ohos:{conf_name}", default="", check_type=str)
        candidates = [configured]
        for root in (
            os.environ.get("OHOS_SDK_ROOT", ""),
            os.environ.get("OHOS_NDK_HOME", ""),
        ):
            if root:
                candidates.append(os.path.join(root, "bin", executable))
                candidates.append(os.path.join(root, "native", "llvm", "bin", executable))
        candidates.append(os.path.join("/data/service/hnp/bin", executable))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def package_info(self):
        self.cpp_info.libs = ["gdal"]
        self.cpp_info.set_property("cmake_file_name", "GDAL")
        self.cpp_info.set_property("cmake_target_name", "GDAL::GDAL")
        self.cpp_info.set_property("pkg_config_name", "gdal")
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
