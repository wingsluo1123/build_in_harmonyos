#!/usr/bin/env python3
"""Conan recipe - MapServer 8.6.5 (cmake).

High-difficulty first pass: keep libmapserver and CLI/CGI utilities with the
mandatory geospatial stack, while disabling optional server/database/rendering
features that would require a much larger unproven dependency closure on OHOS.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, get
from conan.tools.cmake import CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv


class MapserverConan(ConanFile):
    name = "mapserver"
    version = "8.6.5"
    description = "Open source geospatial server and map rendering engine"
    license = "MIT-style"
    homepage = "https://mapserver.org/"
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
        self.requires("gdal/3.9.2")
        self.requires("proj/9.3.1")
        self.requires("libpng/1.6.58")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("freetype/2.14.3")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualBuildEnv(self).generate()

    def _ohos_toolchain(self):
        user_toolchains = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        sdk_root = self.conf.get("user.ohos:sdk_root", default="", check_type=str)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(user_toolchains)
        if sdk_root:
            candidates.append(os.path.join(sdk_root, "ohos", "native", "build", "cmake", "ohos.toolchain.cmake"))
            candidates.append(os.path.join(sdk_root, "native", "build", "cmake", "ohos.toolchain.cmake"))
        if ndk:
            candidates.append(os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake"))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "Cannot find ohos.toolchain.cmake. Set OHOS_NDK_HOME or profile "
            "tools.cmake.cmaketoolchain:user_toolchain or user.ohos:sdk_root."
        )

    def _ohos_arch(self):
        arch = str(self.settings.arch)
        arch_map = {
            "armv8": "arm64-v8a",
            "armv8.3": "arm64-v8a",
            "armv8.4": "arm64-v8a",
            "armv8.5": "arm64-v8a",
            "armv8.6": "arm64-v8a",
            "armv8.7": "arm64-v8a",
            "armv8.8": "arm64-v8a",
            "armv8_32": "armeabi-v7a",
            "armv7": "armeabi-v7a",
            "x86": "x86",
            "x86_64": "x86_64",
        }
        if arch not in arch_map:
            raise ConanInvalidConfiguration(f"Unsupported OHOS architecture: {arch}")
        return arch_map[arch]

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

        gdal = self.dependencies["gdal"].package_folder
        proj = self.dependencies["proj"].package_folder
        png = self.dependencies["libpng"].package_folder
        jpeg = self.dependencies["libjpeg-turbo"].package_folder
        freetype = self.dependencies["freetype"].package_folder

        gdal_lib = self._library("gdal", ["libgdal.so", "libgdal.a"])
        proj_lib = self._library("proj", ["libproj.so", "libproj.a"])
        png_lib = self._library("libpng", ["libpng16.so", "libpng16.a", "libpng.so"])
        jpeg_lib = self._library("libjpeg-turbo", ["libjpeg.so", "libjpeg.a"])
        freetype_lib = self._library("freetype", ["libfreetype.so", "libfreetype.a"])

        libdirs = [os.path.join(dep.package_folder, "lib") for dep in self.dependencies.values()]
        linker_flags = " ".join(
            "-L{0} -Wl,-rpath-link,{0}".format(path) for path in libdirs
        )

        defs = [
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            '-DCMAKE_EXE_LINKER_FLAGS="{}"'.format(linker_flags),
            '-DCMAKE_SHARED_LINKER_FLAGS="{}"'.format(linker_flags),
            "-DBUILD_DYNAMIC={}".format("ON" if self.options.shared else "OFF"),
            "-DBUILD_STATIC=OFF",
            "-DBUILD_TESTING=ON",
            "-DBUILD_FUZZER_REPRODUCER=OFF",
            "-DFUZZER=OFF",
            "-DINSTALL_HTML_BOOTSTRAP=OFF",
            '-DGDAL_INCLUDE_DIR="{}"'.format(os.path.join(gdal, "include")),
            '-DGDAL_LIBRARY="{}"'.format(gdal_lib),
            '-DGDAL_CONFIG="{}"'.format(os.path.join(gdal, "bin", "gdal-config")),
            '-DPROJ_INCLUDE_DIR="{}"'.format(os.path.join(proj, "include")),
            '-DPROJ_LIBRARY="{}"'.format(proj_lib),
            '-DPNG_PNG_INCLUDE_DIR="{}"'.format(os.path.join(png, "include")),
            '-DPNG_INCLUDE_DIR="{}"'.format(os.path.join(png, "include")),
            '-DPNG_LIBRARY="{}"'.format(png_lib),
            '-DPNG_LIBRARY_RELEASE="{}"'.format(png_lib),
            '-DJPEG_INCLUDE_DIR="{}"'.format(os.path.join(jpeg, "include")),
            '-DJPEG_LIBRARY="{}"'.format(jpeg_lib),
            '-DJPEG_LIBRARY_RELEASE="{}"'.format(jpeg_lib),
            '-DFREETYPE_INCLUDE_DIRS="{};{}"'.format(
                os.path.join(freetype, "include", "freetype2"),
                os.path.join(freetype, "include"),
            ),
            '-DFREETYPE_INCLUDE_DIR_freetype2="{}"'.format(os.path.join(freetype, "include", "freetype2")),
            '-DFREETYPE_INCLUDE_DIR_ft2build="{}"'.format(os.path.join(freetype, "include", "freetype2")),
            '-DFREETYPE_LIBRARY="{}"'.format(freetype_lib),
            "-DWITH_WMS=ON",
            "-DWITH_PROTOBUFC=OFF",
            "-DWITH_FCGI=OFF",
            "-DWITH_GEOS=OFF",
            "-DWITH_POSTGIS=OFF",
            "-DWITH_GIF=OFF",
            "-DWITH_FRIBIDI=OFF",
            "-DWITH_HARFBUZZ=OFF",
            "-DWITH_ICONV=OFF",
            "-DWITH_CAIRO=OFF",
            "-DWITH_LIBXML2=OFF",
            "-DWITH_WFS=OFF",
            "-DWITH_WCS=OFF",
            "-DWITH_OGCAPI=OFF",
            "-DWITH_CURL=OFF",
            "-DWITH_CLIENT_WMS=OFF",
            "-DWITH_CLIENT_WFS=OFF",
            "-DWITH_THREAD_SAFETY=OFF",
            "-DWITH_PCRE2=OFF",
            "-DWITH_PYTHON=OFF",
            "-DWITH_PHP=OFF",
            "-DWITH_PERL=OFF",
            "-DWITH_RUBY=OFF",
            "-DWITH_JAVA=OFF",
            "-DWITH_CSHARP=OFF",
        ]
        if str(self.settings.os) == "OHOS":
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
        if can_run(self):
            self.run('ctest --test-dir "{}" --output-on-failure'.format(build_dir), env="conanbuild")
        else:
            self.output.info("cross-building: upstream CTest execution skipped")

    def package(self):
        build_dir = os.path.join(self.build_folder, "build-ohos")
        self.run(
            'cmake --install "{}" --prefix "{}"'.format(build_dir, self.package_folder),
            env="conanbuild",
        )
        if self.options.shared and str(self.settings.os) == "OHOS":
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
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def package_info(self):
        self.cpp_info.libs = ["mapserver"]
        self.cpp_info.set_property("cmake_file_name", "mapserver")
        self.cpp_info.set_property("cmake_target_name", "mapserver::mapserver")
        self.cpp_info.bindirs = ["bin"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
