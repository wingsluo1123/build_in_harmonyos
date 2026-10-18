#!/usr/bin/env python3
"""Conan recipe for plotsauce 0-0.1 — Survex .3d to XML converter (Qt5 CLI tool).

Upstream build system is QBS (plotsauce.qbs, Qt Build Suite) and the repository
does not ship the external "cavern-3dReader" product its .qbs file depends on.
Following the Debian packaging precedent (and the dewalls 1.0.0 recipe in this
archive collection):
  - the recipe ships a CMakeLists.txt (patches/) that builds the same target
    declared upstream (the "plotsauce" console application);
  - the survex .3d reader (src/survex/img.c + img.h, byte-identical img.h to
    survex 1.2.44) is vendored from the official survex 1.2.44 tarball, which
    is declared as a second source in conandata.yml.

Dependencies: qt/5.15.19 (Core + Xml only; upstream also lists Gui but no
source file includes any QtGui header) and zlib (used by the vendored img.c).
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class PlotsauceConan(ConanFile):
    name = "plotsauce"
    version = "0-0.1"
    description = "Qt5 command-line converter from Survex .3d survey files to XML"
    license = "GPL-2.0-or-later"  # upstream LICENSE: GPLv2+; vendored img.c is GPLv2+
    homepage = "https://github.com/Cavewhere/plotsauce"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # visible=False: qt/5.15.19 ships its own Qt5Config.cmake
        # (cmake_find_mode=none), so CMakeDeps cannot generate a qt proxy target
        # for downstream find_dependency(qt) (dewalls precedent). plotsauce is a
        # self-contained application; consumers run the binary and do not need
        # to resolve Qt themselves.
        self.requires("qt/5.15.19", visible=False)
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True,
            filename="plotsauce-source.tar.gz")
        get(self, **self.conan_data["sources"][1],
            filename="survex-1.2.44.tar.gz")  # keep survex-1.2.44/ root dir
        # Vendor the survex .3d reader into src/survex/ exactly where the
        # Debian-patched plotsauce.qbs expects it ("src/survex/*.c|h").
        copy(self, "img.c",
             src=os.path.join(self.source_folder, "survex-1.2.44", "src"),
             dst=os.path.join(self.source_folder, "src", "survex"))
        copy(self, "img.h",
             src=os.path.join(self.source_folder, "survex-1.2.44", "src"),
             dst=os.path.join(self.source_folder, "src", "survex"))

    def generate(self):
        tc = CMakeToolchain(self)
        # qt/5.15.19 ships its own Qt5Config.cmake (cmake_find_mode=none); point
        # CMake at the qt package folder so find_package(Qt5) resolves (same
        # pattern as the dewalls recipe).
        tc.cache_variables["CMAKE_PREFIX_PATH"] = \
            self.dependencies["qt"].package_folder
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def _sdk_llvm_lib_dirs(self):
        """Resolve the OHOS SDK native llvm/lib directory (libc++_shared.so
        needed at runtime by the Qt5 libraries) without hardcoding a
        machine-local absolute path. Derived from the profile-declared
        toolchain (conf tools.build:compiler_executables), same pattern as
        the dewalls 1.0.0 recipe. An explicit OHOS_NATIVE_LLVM_LIB override
        wins when set. Only existing directories are injected.
        """
        dirs = []

        def _collect(base):
            if not base or not os.path.isdir(base):
                return
            for sub in (base, os.path.join(base, "aarch64-linux-ohos")):
                if os.path.isdir(sub) and sub not in dirs:
                    dirs.append(sub)

        env = os.environ.get("OHOS_NATIVE_LLVM_LIB", "").strip()
        if env:
            _collect(env)
            if dirs:
                return dirs

        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
            cxx = compilers.get("cpp") or compilers.get("c")
        except Exception:
            cxx = None
        if cxx and isinstance(cxx, str) and os.path.isabs(cxx):
            prefix = os.path.dirname(os.path.dirname(os.path.normpath(cxx)))
            for hit in glob.glob(os.path.join(
                    prefix, "ohos-sdk.org", "*", "ohos", "native", "llvm", "lib")):
                _collect(hit)
        return dirs

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # Runtime: the plotsauce binary links Qt5 dynamically (qt package is a
        # private requirement, visible=False). Guarded lookup: in downstream
        # consumer graphs qt may be skipped (algobox precedent); when present,
        # make the Qt lib directory discoverable. The OHOS SDK
        # libc++_shared.so directories are always injected (dewalls precedent).
        qt_dep = self.dependencies.get("qt")
        if qt_dep and qt_dep.package_folder:
            qt_lib = os.path.join(qt_dep.package_folder, "lib")
            if os.path.isdir(qt_lib):
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", qt_lib)
        for sub in self._sdk_llvm_lib_dirs():
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", sub)
