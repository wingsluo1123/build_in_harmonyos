#!/usr/bin/env python3
"""Conan recipe — boost 1.84.0 (manual compilation of select libraries).

Boost b2 build system is incompatible with OHOS, so we manually compile
the needed non-header-only libraries: filesystem, regex, program_options,
iostreams. System and date_time are header-only since Boost 1.69.
"""
import os, glob, subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostConan(ConanFile):
    name = "boost"
    version = "1.84.0"
    description = "Boost C++ Libraries 1.84.0（手动编译 4 个库：filesystem/regex/program_options/system，鸿蒙 PC 适配）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = ""
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    # Conan 2 requires `shared` to be declared for package_type="library".
    # Boost b2 build system is incompatible with OHOS, so we manually compile
    # select non-header-only libraries into static archives. Dynamic library
    # building would require b2 (which fails on OHOS), so `shared` is fixed to
    # False — see notes.md for the rationale.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def _compile_lib(self, lib_name, src_dir, src_files, cxx, cxxflags):
        """Compile source files and archive into a static library."""
        objects = []
        obj_dir = os.path.join(self.build_folder, f"obj_{lib_name}")
        os.makedirs(obj_dir, exist_ok=True)
        for src in src_files:
            src_path = os.path.join(src_dir, src)
            obj_name = src.replace("/", "_").replace(".cpp", ".o")
            obj_path = os.path.join(obj_dir, obj_name)
            cmd = f"{cxx} {cxxflags} -c {src_path} -o {obj_path}"
            self.run(cmd)
            objects.append(obj_path)
        lib_path = os.path.join(self.build_folder, f"libboost_{lib_name}.a")
        self.run(f"llvm-ar rcs {lib_path} {' '.join(objects)}")
        return lib_path

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")

        boost_root = self.source_folder
        # Optimization flags driven by build_type (R8: no hardcoded build profile).
        if self.settings.build_type == "Debug":
            opt_flags = ["-O0", "-g"]
        else:
            opt_flags = ["-O2", "-DNDEBUG"]
        cxxflags = " ".join([
            "-std=c++17",
            "-stdlib=libc++",
            *opt_flags,
            "-fPIC",
            f"-I{boost_root}",
            "-DBOOST_ALL_NO_LIB",
            "-DBOOST_SYSTEM_NO_DEPRECATED",
            "-DBOOST_FILESYSTEM_NO_CXX20_CHAR8_T",
            "-DBOOST_FILESYSTEM_NO_CXX20_ATOMIC_REF",
            "-DBOOST_IOSTREAMS_NO_LIB",
            # R8 compliance: skip pthread_setcancelstate (not available on OHOS musl)
            # via a feature-detection macro instead of a platform macro (__OHOS__).
            # The patch consumes BOOST_SP_NO_PTHREAD_SETCANCELSTATE, see patches/0001.
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
            f"-I{os.path.join(self.dependencies['zlib'].package_folder, 'include')}",
        ])

        # Filesystem: skip windows_file_codecvt.cpp (Windows only)
        fs_src = [
            "codecvt_error_category.cpp", "directory.cpp", "exception.cpp",
            "operations.cpp", "path.cpp", "path_traits.cpp",
            "portability.cpp", "unique_path.cpp", "utf8_codecvt_facet.cpp",
        ]
        self._compile_lib("filesystem", os.path.join(boost_root, "libs/filesystem/src"), fs_src, cxx, cxxflags)

        # Regex
        re_src = [
            "posix_api.cpp", "regex.cpp", "regex_debug.cpp",
            "static_mutex.cpp", "wide_posix_api.cpp",
        ]
        self._compile_lib("regex", os.path.join(boost_root, "libs/regex/src"), re_src, cxx, cxxflags)

        # ProgramOptions: skip winmain.cpp (Windows only)
        po_src = [
            "cmdline.cpp", "config_file.cpp", "Convert.cpp",
            "options_description.cpp", "parsers.cpp", "positional_options.cpp",
            "split.cpp", "utf8_codecvt_facet.cpp", "value_semantic.cpp",
            "variables_map.cpp",
        ]
        self._compile_lib("program_options", os.path.join(boost_root, "libs/program_options/src"), po_src, cxx, cxxflags)

        # Iostreams: compile the core files + zlib (skip bzip2/lzma/zstd - no system libs)
        io_src = [
            "file_descriptor.cpp", "gzip.cpp", "mapped_file.cpp", "zlib.cpp",
        ]
        self._compile_lib("iostreams", os.path.join(boost_root, "libs/iostreams/src"), io_src, cxx, cxxflags)

    def package(self):
        # Install headers: copy entire boost/ include directory
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

        # Install compiled static libraries
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_*.a")):
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")

        # Main "headers" component (always needed)
        self.cpp_info.components["boost_headers"].includedirs = ["include"]
        # R8 compliance: expose BOOST_SP_NO_PTHREAD_SETCANCELSTATE to all
        # consumers so the patched sp_thread_sleep.hpp skips the
        # pthread_setcancelstate path (not available on OHOS musl) without
        # relying on a platform macro. Every downstream that includes boost
        # headers gets this define via Conan's CMakeDeps/Toolchain propagation.
        self.cpp_info.components["boost_headers"].defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        self.cpp_info.components["boost_headers"].set_property("cmake_target_name", "Boost::headers")

        # Filesystem
        self.cpp_info.components["boost_filesystem"].includedirs = []
        self.cpp_info.components["boost_filesystem"].libs = ["boost_filesystem"]
        self.cpp_info.components["boost_filesystem"].requires = ["boost_headers", "boost_system"]
        self.cpp_info.components["boost_filesystem"].set_property("cmake_target_name", "Boost::filesystem")

        # Regex
        self.cpp_info.components["boost_regex"].includedirs = []
        self.cpp_info.components["boost_regex"].libs = ["boost_regex"]
        self.cpp_info.components["boost_regex"].requires = ["boost_headers"]
        self.cpp_info.components["boost_regex"].set_property("cmake_target_name", "Boost::regex")

        # ProgramOptions
        self.cpp_info.components["boost_program_options"].includedirs = []
        self.cpp_info.components["boost_program_options"].libs = ["boost_program_options"]
        self.cpp_info.components["boost_program_options"].requires = ["boost_headers"]
        self.cpp_info.components["boost_program_options"].set_property("cmake_target_name", "Boost::program_options")

        # Iostreams
        self.cpp_info.components["boost_iostreams"].includedirs = []
        self.cpp_info.components["boost_iostreams"].libs = ["boost_iostreams"]
        self.cpp_info.components["boost_iostreams"].requires = ["boost_headers", "boost_system"]
        self.cpp_info.components["boost_iostreams"].set_property("cmake_target_name", "Boost::iostreams")

        # System (header-only since 1.69, but CMake component still needed)
        self.cpp_info.components["boost_system"].includedirs = []
        self.cpp_info.components["boost_system"].libs = []
        self.cpp_info.components["boost_system"].requires = ["boost_headers"]
        self.cpp_info.components["boost_system"].set_property("cmake_target_name", "Boost::system")

        # DateTime (header-only since 1.69, but CMake component still needed)
        self.cpp_info.components["boost_date_time"].includedirs = []
        self.cpp_info.components["boost_date_time"].libs = []
        self.cpp_info.components["boost_date_time"].requires = ["boost_headers"]
        self.cpp_info.components["boost_date_time"].set_property("cmake_target_name", "Boost::date_time")
