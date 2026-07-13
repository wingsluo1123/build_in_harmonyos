#!/usr/bin/env python3
"""Conan recipe — Ice (ZeroC) 3.8.2 for HarmonyOS PC.

Ice uses a custom Makefile-based build system (not autotools/cmake/meson).
Builds C++ core libraries: Ice, IceUtil, IceBox, Glacier2, IceGrid, IceStorm.

HarmonyOS adaptation:
  - Symlink config/Make.rules.HarmonyOS -> Make.rules.Linux (uname returns HarmonyOS)
  - Install via cp since install(1) is not available on OHOS
  - Skip DataStorm (uses C++20 structured binding capture, needs -std=c++20)
"""
import os
import shlex
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class IceConan(ConanFile):
    name = "ice"
    version = "3.8.2"
    description = "ZeroC Ice - Comprehensive RPC framework for C++, Python, Java and more."
    license = "GPL-2.0-only"
    homepage = "https://github.com/zeroc-ice/ice"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("bzip2/1.0.8")
        self.requires("expat/2.8.0")
        self.requires("libedit/20240817")
        self.requires("lmdb/0.9.35")
        self.requires("mcpp/2.7.2")
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R32: Cross-platform settings check
        pass

    def build(self):
        apply_conandata_patches(self)

        # Step 1: Create HarmonyOS platform symlink for Ice's build system
        # Ice uses $(shell uname) to select Make.rules.$(os).
        # HarmonyOS returns "HarmonyOS", so we need Make.rules.HarmonyOS -> Make.rules.Linux
        rules_dir = os.path.join(self.source_folder, "config")
        ohos_rules = os.path.join(rules_dir, "Make.rules.HarmonyOS")
        if not os.path.exists(ohos_rules):
            os.symlink("Make.rules.Linux", ohos_rules)

        # Step 2: Build C++ core libraries
        # R9: Use -j1
        # R33: Get compiler from profile/environment
        cc = os.environ.get("CC", "clang")
        cxx = os.environ.get("CXX", "clang++")
        ar = os.environ.get("AR", "llvm-ar")

        cpp_dir = os.path.join(self.source_folder, "cpp")

        # R9: Use -j1
        # Build C++ core libraries - exclude DataStorm (C++20 structured binding)
        # The top-level Makefile includes every */Makefile.mk discovered by find(1),
        # so we disable DataStorm's Makefile.mk before evaluating projects.
        datastorm_mk = os.path.join(cpp_dir, "src", "DataStorm", "Makefile.mk")
        if os.path.exists(datastorm_mk):
            with open(datastorm_mk, "w") as f:
                f.write("# DataStorm disabled on OHOS: requires C++20 structured binding capture.\n")

        def _abs_paths(dep, paths):
            return [path if os.path.isabs(path) else os.path.join(dep.package_folder, path) for path in paths]

        dep_homes = {
            "BZ2_HOME": self.dependencies["bzip2"].package_folder,
            "EXPAT_HOME": self.dependencies["expat"].package_folder,
            "LMDB_HOME": self.dependencies["lmdb"].package_folder,
            "MCPP_HOME": self.dependencies["mcpp"].package_folder,
        }
        include_flags = []
        lib_flags = []
        for dep_name in ("bzip2", "expat", "libedit", "lmdb", "mcpp", "openssl", "zlib"):
            dep = self.dependencies[dep_name]
            include_flags.extend(f"-I{path}" for path in _abs_paths(dep, dep.cpp_info.includedirs))
            lib_flags.extend(f"-L{path}" for path in _abs_paths(dep, dep.cpp_info.libdirs))

        mcpp_dep = self.dependencies["mcpp"]
        mcpp_includedirs = _abs_paths(mcpp_dep, mcpp_dep.cpp_info.includedirs) or [os.path.join(mcpp_dep.package_folder, "include")]
        mcpp_libdirs = _abs_paths(mcpp_dep, mcpp_dep.cpp_info.libdirs) or [os.path.join(mcpp_dep.package_folder, "lib")]
        mcpp_libs = mcpp_dep.cpp_info.libs or ["mcpp"]
        mcpp_ldflags = [f"-L{path}" for path in mcpp_libdirs] + [f"-l{lib}" for lib in mcpp_libs]

        make_vars = {
            "CC": cc,
            "CXX": cxx,
            "AR": ar,
            "CPPFLAGS": " ".join(include_flags),
            "LDFLAGS": " ".join(lib_flags),
            "mcpp_includedir": mcpp_includedirs[0],
            "mcpp_libdir": mcpp_libdirs[0],
            "mcpp_ldflags": " ".join(mcpp_ldflags),
            "SHELL": "/data/service/hnp/bin/bash",
            **dep_homes,
        }
        make_args = " ".join(f"{key}={shlex.quote(value)}" for key, value in make_vars.items())

        targets = "Slice IceUtil slice2cpp Ice IceBox icebox iceboxadmin Glacier2 IceStorm IceDiscovery IceLocatorDiscovery"
        self.run(f"make -C {cpp_dir} {targets} OPTIMIZE=yes PLATFORMS=aarch64 CONFIGS=shared "
                 f"{make_args} -j1")

    def package(self):
        # Install using cp since install(1) is not available on HarmonyOS
        src = self.source_folder
        pkg_lib = os.path.join(self.package_folder, "lib")
        pkg_bin = os.path.join(self.package_folder, "bin")
        pkg_inc = os.path.join(self.package_folder, "include")

        copy(self, "*.so*", os.path.join(src, "cpp", "lib64"), pkg_lib)
        copy(self, "*.a", os.path.join(src, "cpp", "lib64"), pkg_lib)
        copy(self, "*", os.path.join(src, "cpp", "bin"), pkg_bin)
        copy(self, "*", os.path.join(src, "cpp", "include"), pkg_inc)
        # Ice public headers include generated headers as "Ice/Version.h".
        # Install generated headers into both include/generated and include for CMake consumers.
        copy(self, "*.h", os.path.join(src, "cpp", "include", "generated"), pkg_inc)

    def package_info(self):
        # Core libraries
        self.cpp_info.libs = [
            "Ice",
            "IceUtil",
            "Slice",
            "IceBox",
            "Glacier2",
            "IceStorm",
            "IceDiscovery",
            "IceLocatorDiscovery",
        ]
        # C++ standard, generated Slice headers, executable tools, and threading
        self.cpp_info.includedirs = ["include", "include/generated"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.cxxflags = ["-std=c++17", "-pthread"]
        self.cpp_info.system_libs = ["dl", "pthread", "rt"]
