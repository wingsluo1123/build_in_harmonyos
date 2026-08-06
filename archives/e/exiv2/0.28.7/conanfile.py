#!/usr/bin/env python3
"""Conan recipe for exiv2 0.28.7 — CMake-based EXIF/IPTC/XMP metadata library.

Build approach:
- CMake build system (exiv2 uses CMake, not Meson)
- Dependencies: zlib, expat, brotli from conan; inih built from source
  (conan inih/r58 doesn't include INIReader C++ wrapper)
- Static library by default
- Target name fixes in build(): exiv2 expects EXPAT::EXPAT, ZLIB::ZLIB,
  ${Brotli_LIBRARIES}, inih::inireader/libinih, BROTLI_FOUND, etc.
  but conan CMakeDeps generates lowercase targets and mixed-case variables.
  We fix all mismatches with replace_in_file().
"""
import os
from conan import ConanFile
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches,
    replace_in_file, copy, save,
)
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class Exiv2Conan(ConanFile):
    name = "exiv2"
    version = "0.28.7"
    description = "EXIF/IPTC/XMP C++ metadata library and tools"
    license = "GPL-2.0"
    homepage = "https://github.com/exiv2/exiv2"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("expat/2.8.2")
        self.requires("brotli/1.2.0")
        # inih is built from source (conan inih/r58 lacks INIReader C++ wrapper)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(self, **self.conan_data["inih_sources"], strip_root=True,
            destination=os.path.join(self.source_folder, "inih_src"))

    def generate(self):
        # CMakeDeps for conan-managed dependencies
        deps = CMakeDeps(self)
        deps.generate()

        # CMakeToolchain
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["EXIV2_ENABLE_NLS"] = False
        tc.variables["EXIV2_ENABLE_WEBREADY"] = False
        tc.variables["EXIV2_BUILD_SAMPLES"] = False
        tc.variables["EXIV2_BUILD_UNIT_TESTS"] = False
        tc.variables["EXIV2_BUILD_DOC"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # --- Fix target name and variable mismatches ---
        src_cmake = os.path.join(self.source_folder, "src", "CMakeLists.txt")

        # EXPAT::EXPAT -> expat::expat
        replace_in_file(self, src_cmake, "EXPAT::EXPAT", "expat::expat")
        # ZLIB::ZLIB -> zlib::zlib
        replace_in_file(self, src_cmake, "ZLIB::ZLIB", "zlib::zlib")
        # Remove ZLIB_INCLUDE_DIR (conan target handles includes)
        replace_in_file(self, src_cmake,
                        "    target_include_directories(exiv2lib_int PRIVATE ${ZLIB_INCLUDE_DIR})",
                        "")
        # BROTLI_FOUND -> Brotli_FOUND (CMake config mode sets mixed-case)
        replace_in_file(self, src_cmake, "BROTLI_FOUND", "Brotli_FOUND")
        # ${Brotli_LIBRARIES} -> brotli::brotli target
        replace_in_file(self, src_cmake,
                        "target_link_libraries( exiv2lib PRIVATE ${Brotli_LIBRARIES})",
                        "target_link_libraries( exiv2lib PRIVATE brotli::brotli)")
        # Remove Brotli_INCLUDE_DIRS line (conan target handles includes)
        replace_in_file(self, src_cmake,
                        "    target_include_directories(exiv2lib PRIVATE ${Brotli_INCLUDE_DIRS})",
                        "")
        # inih::inireader and inih::libinih -> inih::inih
        replace_in_file(self, src_cmake, "inih::inireader", "inih::inih")
        replace_in_file(self, src_cmake, "inih::libinih", "inih::inih")

        # Fix xmpsdk/CMakeLists.txt — link expat target for include dirs
        xmpsdk_cmake = os.path.join(self.source_folder, "xmpsdk", "CMakeLists.txt")
        replace_in_file(self, xmpsdk_cmake,
                        "        ${EXPAT_INCLUDE_DIRS}\n)",
                        "\n)\ntarget_link_libraries(exiv2-xmp PRIVATE expat::expat)")

        # Fix generateConfigFile.cmake and printSummary.cmake
        gen_cfg = os.path.join(self.source_folder, "cmake", "generateConfigFile.cmake")
        replace_in_file(self, gen_cfg, "BROTLI_FOUND", "Brotli_FOUND")
        print_sum = os.path.join(self.source_folder, "cmake", "printSummary.cmake")
        replace_in_file(self, print_sum, "BROTLI_FOUND", "Brotli_FOUND")

        # Remove custom find modules that conflict with CMakeDeps
        for fname in ("Findinih.cmake", "FindBrotli.cmake"):
            fpath = os.path.join(self.source_folder, "cmake", fname)
            if os.path.exists(fpath):
                os.remove(fpath)

        # --- Build inih from source (ini.c + INIReader.cpp) ---
        inih_src = os.path.join(self.source_folder, "inih_src")
        build_dir = self.build_folder
        ce = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict) or {}
        cc = ce.get("c", "clang")
        cxx = ce.get("cpp", "clang++")
        ar = ce.get("ar") or ""
        if not ar:
            cc_path = (ce.get("c") or "").strip()
            if cc_path:
                bindir = os.path.dirname(cc_path)
                for cand in ("llvm-ar", "ar"):
                    full = os.path.join(bindir, cand)
                    if os.path.isfile(full):
                        ar = full
                        break
        ar = ar or "ar"

        self.run(f'"{cc}" -c -O2 -fPIC -I"{inih_src}" '
                 f'-o "{build_dir}/ini.o" "{inih_src}/ini.c"')
        self.run(f'"{cxx}" -c -O2 -fPIC -std=c++17 '
                 f'-I"{inih_src}" -I"{inih_src}/cpp" '
                 f'-o "{build_dir}/INIReader.o" '
                 f'"{inih_src}/cpp/INIReader.cpp"')
        self.run(f'"{ar}" rcs "{build_dir}/libinih.a" "{build_dir}/ini.o"')
        self.run(f'"{ar}" rcs "{build_dir}/libINIReader.a" '
                 f'"{build_dir}/INIReader.o"')

        # Install inih to a prefix and create cmake config
        inih_prefix = os.path.join(build_dir, "inih_install")
        for d in ("include", "lib/cmake/inih"):
            os.makedirs(os.path.join(inih_prefix, d), exist_ok=True)
        copy(self, "ini.h", inih_src,
             os.path.join(inih_prefix, "include"))
        copy(self, "INIReader.h", os.path.join(inih_src, "cpp"),
             os.path.join(inih_prefix, "include"))
        copy(self, "libinih.a", build_dir,
             os.path.join(inih_prefix, "lib"))
        copy(self, "libINIReader.a", build_dir,
             os.path.join(inih_prefix, "lib"))

        inih_cfg = (
            f'set(inih_INCLUDE_DIRS "{inih_prefix}/include")\n'
            f'set(inih_INCLUDE_DIR "{inih_prefix}/include")\n'
            f'set(inih_LIBRARIES "inih;INIReader")\n'
            f'set(inih_FOUND TRUE)\n'
            f'if(NOT TARGET inih::inih)\n'
            f'    add_library(inih::inih INTERFACE IMPORTED)\n'
            f'    set_property(TARGET inih::inih PROPERTY '
            f'INTERFACE_INCLUDE_DIRECTORIES "{inih_prefix}/include")\n'
            f'    set_property(TARGET inih::inih PROPERTY '
            f'INTERFACE_LINK_LIBRARIES '
            f'"{inih_prefix}/lib/libinih.a;{inih_prefix}/lib/libINIReader.a")\n'
            f'endif()\n'
        )
        save(self, os.path.join(inih_prefix, "lib", "cmake", "inih",
                                "inih-config.cmake"), inih_cfg)

        # --- Build exiv2 with cmake ---
        cmake = CMake(self)
        cmake.configure({"CMAKE_PREFIX_PATH": inih_prefix})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Copy inih libraries (built from source) into the package
        # so consumers can resolve INIReader/inih symbols from libexiv2.a
        copy(self, "libinih.a", self.build_folder,
             os.path.join(self.package_folder, "lib"))
        copy(self, "libINIReader.a", self.build_folder,
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # exiv2 static lib has unresolved INIReader/inih symbols;
        # consumers must link them too
        self.cpp_info.libs = ["exiv2", "INIReader", "inih"]
        self.cpp_info.set_property("cmake_file_name", "exiv2")
        self.cpp_info.set_property("cmake_target_name", "exiv2::exiv2")
        self.cpp_info.requires = ["zlib::zlib", "expat::expat",
                                  "brotli::brotli"]
