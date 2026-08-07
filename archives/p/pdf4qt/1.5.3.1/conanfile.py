#!/usr/bin/env python3
"""Conan recipe for pdf4qt 1.5.3.1 — HarmonyOS PC platform adaptation.

PDF4QT is an open-source PDF editor based on Qt6. This recipe builds the
core library (Pdf4QtLibCore) with vendored blend2d (2D vector graphics engine).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class Pdf4QtConan(ConanFile):
    name = "pdf4qt"
    version = "1.5.3.1"
    description = "Open-source PDF editor and library based on Qt6 (core library)"
    license = "MIT"
    homepage = "https://jakubmelka.github.io/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("openssl/3.5.6.1.1")
        self.requires("freetype/2.14.3")
        self.requires("openjpeg/2.5.4")
        self.requires("libjpeg/10")
        self.requires("libpng/1.6.58")
        self.requires("lcms2/2.19")
        self.requires("zlib/1.3.1.1")
        self.requires("fontconfig/2.18.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Download pdf4qt source
        get(self, **self.conan_data["sources"], strip_root=True)

        # Download blend2d source (vendored - not in Conan repo)
        blend2d_data = self.conan_data["blend2d"]
        get(self, url=blend2d_data["url"], sha256=blend2d_data["sha256"],
            destination=os.path.join(self.source_folder, "blend2d-src"),
            strip_root=True)

        # Download asmjit source (blend2d JIT dependency)
        asmjit_data = self.conan_data["asmjit"]
        asmjit_dest = os.path.join(self.source_folder, "blend2d-src", "3rdparty", "asmjit")
        os.makedirs(asmjit_dest, exist_ok=True)
        get(self, url=asmjit_data["url"], sha256=asmjit_data["sha256"],
            destination=asmjit_dest, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Build only core library (Qt6Svg/PrintSupport/TextToSpeech not available)
        tc.variables["PDF4QT_BUILD_ONLY_CORE_LIBRARY"] = "ON"
        tc.variables["PDF4QT_INSTALL_INCLUDE"] = "ON"
        # Set blend2d_DIR to point to the installed blend2d cmake config
        blend2d_install = os.path.join(self.build_folder, "blend2d-install")
        blend2d_cmake_dir = os.path.join(blend2d_install, "lib", "cmake", "blend2d")
        tc.variables["blend2d_DIR"] = blend2d_cmake_dir
        # Also add blend2d install to CMAKE_PREFIX_PATH as fallback
        tc.variables["CMAKE_PREFIX_PATH"] = blend2d_install
        # Set Qt6_DIR to point to the qtbase package's Qt6 cmake config
        qtbase = self.dependencies["qtbase"]
        qt6_cmake_dir = os.path.join(qtbase.package_folder, "lib", "cmake", "Qt6")
        tc.variables["Qt6_DIR"] = qt6_cmake_dir
        # Set OpenJPEG_DIR if the package provides its own cmake config
        openjpeg = self.dependencies["openjpeg"]
        openjpeg_cmake_dir = os.path.join(openjpeg.package_folder, "lib", "cmake")
        if os.path.isdir(openjpeg_cmake_dir):
            # Find the OpenJPEG cmake config subdirectory
            for d in os.listdir(openjpeg_cmake_dir):
                if "openjpeg" in d.lower():
                    tc.variables["OpenJPEG_DIR"] = os.path.join(openjpeg_cmake_dir, d)
                    break
        tc.generate()
        # Generate CMakeDeps for all dependencies
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)

        # Step 1: Build blend2d from source (vendored)
        blend2d_src = os.path.join(self.source_folder, "blend2d-src")
        blend2d_build = os.path.join(self.build_folder, "blend2d-build")
        blend2d_install = os.path.join(self.build_folder, "blend2d-install")
        os.makedirs(blend2d_build, exist_ok=True)

        # Configure blend2d with Conan toolchain for cross-compilation
        toolchain_file = os.path.join(self.build_folder, "generators", "conan_toolchain.cmake")
        subprocess.run([
            "cmake", blend2d_src,
            "-DCMAKE_INSTALL_PREFIX=" + blend2d_install,
            "-DCMAKE_BUILD_TYPE=" + str(self.settings.build_type),
            "-DCMAKE_TOOLCHAIN_FILE=" + toolchain_file,
            "-DBLEND2D_STATIC=ON",
            "-DBLEND2D_NO_JIT=OFF",
            "-DBLEND2D_NO_FUTEX=OFF",
            "-DCMAKE_CXX_STANDARD=20",
        ], cwd=blend2d_build, check=True)

        # Build and install blend2d
        subprocess.run(["cmake", "--build", ".", "--", "-j2"],
                       cwd=blend2d_build, check=True)
        subprocess.run(["cmake", "--install", "."],
                       cwd=blend2d_build, check=True)

        # Step 2: Build pdf4qt with blend2d path
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Install blend2d headers and lib to package
        blend2d_install = os.path.join(self.build_folder, "blend2d-install")
        if os.path.isdir(blend2d_install):
            copy(self, "*.h", os.path.join(blend2d_install, "include"),
                 os.path.join(self.package_folder, "include"), excludes="*.in")
            copy(self, "*.a", os.path.join(blend2d_install, "lib"),
                 os.path.join(self.package_folder, "lib"))

        cmake = CMake(self)
        cmake.install()

        # Move shared library from bin/ to lib/ (OHOS CMake treats .so as RUNTIME)
        bin_dir = os.path.join(self.package_folder, "bin")
        lib_dir = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        if os.path.isdir(bin_dir):
            for f in os.listdir(bin_dir):
                if f.endswith(".so") or ".so." in f:
                    src = os.path.join(bin_dir, f)
                    dst = os.path.join(lib_dir, f)
                    if os.path.exists(dst):
                        os.remove(dst)
                    shutil.move(src, dst)

    def package_info(self):
        self.cpp_info.libs = ["Pdf4QtLibCore", "blend2d"]
        self.cpp_info.libdirs = ["lib"]
        # Set cmake file name and target name
        self.cpp_info.set_property("cmake_file_name", "pdf4qt")
        self.cpp_info.set_property("cmake_target_name", "pdf4qt::pdf4qt")
