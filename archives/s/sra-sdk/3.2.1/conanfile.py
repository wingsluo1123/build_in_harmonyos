#!/usr/bin/env python3
"""Conan recipe for sra-sdk 3.2.1 — NCBI SRA Toolkit and SDK.

Upstream releases the toolkit (ncbi/sra-tools) together with the SDK libraries
(ncbi/ncbi-vdb); the toolkit cannot be built without the VDB source tree, so
both trees are fetched and built here, mirroring NCBI's own release process.

HarmonyOS PC (OHOS) adaptations:
- Build with CMAKE_SYSTEM_NAME=Linux/CMAKE_SYSTEM_PROCESSOR=aarch64; the OHOS
  clang already targets aarch64-linux-ohos. sra-tools' env.cmake derives the
  platform from CMAKE_HOST_SYSTEM_*, which reports "HarmonyOS"/"unknown" on
  device, so the recipe patches it to honour the target triple when
  cross-compiling.
- Bison >= 3.8 prefixes the built-in error token, colliding with the parsers'
  <prefix>error callbacks; the vdb grammar patch redirects yyerror.
- OHOS musl has no pthread_cancel(); the BGZF reader thread in ncbi-vdb is
  switched to cooperative cancellation.
- libxml2 2.15 removed ATTRIBUTE_UNUSED; kxml marks the unused parameter in
  the function body instead.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, patch, apply_conandata_patches


class SraSdkConan(ConanFile):
    name = "sra-sdk"
    version = "3.2.1"
    description = "NCBI SRA Toolkit and SDK (Sequence Read Archive tools and libraries)"
    license = "Public Domain"
    homepage = "https://github.com/ncbi/sra-tools"
    url = ""
    # The SDK ships both static NGS/VDB libraries and shared VDB libraries;
    # static-library keeps consumers on the static link path, which is the
    # reliable option on OHOS where dlopen from app data dirs is restricted.
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*", "patches/vdb/*"

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libxml2/2.15.3")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)
        get(self, **self.conan_data["vdb_sources"][self.version],
            destination="ncbi-vdb", strip_root=True)

    def _apply_patches(self, base_path, key):
        for item in self.conan_data.get(key, {}).get(self.version, []):
            patch(self, base_path=base_path, strip=1,
                  patch_file=os.path.join(self.export_sources_folder,
                                          item["patch_file"]))

    def generate(self):
        tc = CMakeToolchain(self)
        dep = self.dependencies["libxml2"]
        cpp_info = dep.cpp_info.aggregated_components()
        xml_inc = cpp_info.includedirs[0]
        if not os.path.exists(os.path.join(xml_inc, "libxml", "xmlreader.h")):
            nested = os.path.join(xml_inc, "libxml2")
            if os.path.exists(os.path.join(nested, "libxml", "xmlreader.h")):
                xml_inc = nested
        xml_lib = os.path.join(cpp_info.libdirs[0], "libxml2.so")
        if not os.path.exists(xml_lib):
            xml_lib = os.path.join(cpp_info.libdirs[0], "libxml2.a")
        # sra-tools looks for the legacy FindLibXml2 variables.
        tc.variables["LIBXML2_INCLUDE_DIR"] = xml_inc
        tc.variables["LIBXML2_LIBRARIES"] = xml_lib
        tc.generate()

    def _system_variables(self):
        if self.settings.os != "OHOS":
            return {}
        arch = {"armv8": "aarch64", "armv7": "armv7l",
                "x86_64": "x86_64"}.get(str(self.settings.arch),
                                        str(self.settings.arch))
        return {"CMAKE_SYSTEM_NAME": "Linux",
                "CMAKE_SYSTEM_PROCESSOR": arch}

    def _dependencies_variables(self, vdb_build, vdb_src):
        return {
            "VDB_LIBDIR": os.path.join(vdb_build, "lib"),
            "VDB_INCDIR": os.path.join(vdb_src, "interfaces"),
            "TOOLS_ONLY": "OFF",
        }

    def build(self):
        sra_src = self.source_folder
        vdb_src = os.path.join(self.source_folder, "ncbi-vdb")
        self._apply_patches(vdb_src, "vdb_patches")
        apply_conandata_patches(self)

        vdb_build = os.path.join(self.build_folder, "vdb")
        sra_build = os.path.join(self.build_folder, "sra")

        variables = dict(self._system_variables())
        variables.update({"LIBS_ONLY": "ON"})
        cmake = CMake(self)
        cmake.configure(build_script_folder="ncbi-vdb",
                        variables=variables, subfolder="vdb")
        cmake.build(subfolder="vdb")

        variables = dict(self._system_variables())
        variables.update(self._dependencies_variables(vdb_build, vdb_src))
        cmake = CMake(self)
        cmake.configure(variables=variables, subfolder="sra")
        cmake.build(subfolder="sra")

    @staticmethod
    def _copy_tree(src, dst, files_only=None):
        """Copy a tree preserving symlinks, falling back to hardlink/copy.

        HMDFS occasionally rejects symlink creation under load (EACCES), so the
        alias chains must degrade gracefully instead of failing the package.
        """
        import shutil

        os.makedirs(dst, exist_ok=True)
        for root, dirs, files in os.walk(src):
            rel = os.path.relpath(root, src)
            target_dir = dst if rel == "." else os.path.join(dst, rel)
            os.makedirs(target_dir, exist_ok=True)
            for name in files:
                if files_only and name not in files_only:
                    continue
                source = os.path.join(root, name)
                target = os.path.join(target_dir, name)
                if os.path.islink(source):
                    if os.path.lexists(target):
                        os.remove(target)
                    link = os.readlink(source)
                    try:
                        os.symlink(link, target)
                        continue
                    except OSError:
                        pass
                    source = os.path.realpath(source)
                if os.path.lexists(target):
                    os.remove(target)
                try:
                    os.link(source, target)
                except OSError:
                    shutil.copy2(source, target)

    def package(self):
        sra_src = self.source_folder
        vdb_src = os.path.join(self.source_folder, "ncbi-vdb")
        sra_build = os.path.join(self.build_folder, "sra")
        vdb_build = os.path.join(self.build_folder, "vdb")
        bin_dir = os.path.join(self.package_folder, "bin")
        lib_dir = os.path.join(self.package_folder, "lib")
        inc_dir = os.path.join(self.package_folder, "include")

        # Preserve the toolkit's versioned alias chains (tool -> tool.3 -> tool.x.y.z).
        self._copy_tree(os.path.join(sra_build, "bin"), bin_dir)
        self._copy_tree(os.path.join(sra_build, "lib"), lib_dir)
        self._copy_tree(os.path.join(vdb_build, "lib"), lib_dir)
        self._copy_tree(os.path.join(vdb_src, "interfaces"), inc_dir)
        self._copy_tree(os.path.join(sra_src, "ngs", "ngs-sdk", "ngs"),
                        os.path.join(inc_dir, "ngs"))
        # The NCBI implementation header is included as <ngs/ncbi/NGS.hpp>;
        # upstream installs it under include/ncbi-vdb as well.
        self._copy_tree(os.path.join(sra_src, "ngs", "ncbi"),
                        os.path.join(inc_dir, "ncbi-vdb"),
                        files_only=("NGS.hpp",))
        copy(self, "NGS.hpp", src=os.path.join(sra_src, "ngs", "ncbi"),
             dst=os.path.join(inc_dir, "ngs", "ncbi"))
        self._copy_tree(os.path.join(vdb_src, "interfaces", "kfg", "ncbi"),
                        os.path.join(self.package_folder, "ncbi"))
        copy(self, "LICENSE", src=sra_src,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE", src=vdb_src,
             dst=os.path.join(self.package_folder, "licenses", "ncbi-vdb"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["ncbi-ngs-c++", "ncbi-ngs",
                              "ncbi-vdb", "ncbi-wvdb"]
