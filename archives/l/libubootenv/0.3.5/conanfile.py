#!/usr/bin/env python3
"""Conan recipe for libubootenv 0.3.5 — CMake build system.

U-Boot environment access library. Produces libubootenv (shared+static)
and fw_printenv/fw_setenv CLI tools.

OHOS adaptation:
- cmake_minimum_required bumped 2.6 → 3.5 (CMake 4.x compat)
- SONAME explicitly set via LINKER:-soname (CMake ignores VERSION/SOVERSION)
- Dependency paths injected at build() stage
- OHOS SDK <mtd/ubi-user.h> bug workaround
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, replace_in_file


class LibubootenvConan(ConanFile):
    name = "libubootenv"
    version = "0.3.5"
    description = "Library to access U-Boot environment (replacement for fw_printenv/fw_setenv)."
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/sbabic/libubootenv"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")
        self.requires("libyaml/0.2.5")

    def layout(self):
        cmake_layout(self)

    def source(self):
        from conan.tools.files import get
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["BUILD_DOC"] = "OFF"
        tc.generate()

    def build(self):
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)
        src_cmake = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        root_cmake = os.path.join(self.source_folder, "CMakeLists.txt")

        # 1) cmake_minimum_required 2.6 → 3.5
        replace_in_file(self, src_cmake,
                        "cmake_minimum_required (VERSION 2.6)",
                        "cmake_minimum_required(VERSION 3.5)")
        replace_in_file(self, root_cmake,
                        "cmake_minimum_required (VERSION 2.6)",
                        "cmake_minimum_required(VERSION 3.5)")

        # 2) Fix SONAME (CMake ignores VERSION/SOVERSION on some platforms)
        #    SONAME must match actual filename (libubootenv.so, no version suffix)
        replace_in_file(self, src_cmake,
                        "SET_TARGET_PROPERTIES(ubootenv PROPERTIES VERSION ${VERSION} SOVERSION ${SOVERSION})",
                        "SET_TARGET_PROPERTIES(ubootenv PROPERTIES VERSION ${VERSION} SOVERSION ${SOVERSION})\ntarget_link_options(ubootenv PRIVATE \"LINKER:-soname,libubootenv.so\")")

        # 3) Get Conan dependency paths (available in build() stage)
        zlib = self.dependencies["zlib"].cpp_info
        yaml = self.dependencies["libyaml"].cpp_info

        def find_lib(cpp_info):
            for lib in cpp_info.libs:
                for ext in [".a", ".so", ".dylib", ".lib"]:
                    candidate = os.path.join(cpp_info.libdirs[0], f"lib{lib}{ext}")
                    if os.path.exists(candidate):
                        return candidate
            return f"-l{cpp_info.libs[0]}"

        zlib_inc = zlib.includedirs[0]
        yaml_inc = yaml.includedirs[0]
        zlib_lib = find_lib(zlib)
        yaml_lib = find_lib(yaml)

        # 4) Inject include dirs and fix link targets
        inject = f"""# OHOS: Conan dependency paths
include_directories("{zlib_inc}" "{yaml_inc}")
"""
        replace_in_file(self, src_cmake,
                        "target_link_libraries(ubootenv z yaml)",
                        inject + f"target_link_libraries(ubootenv {zlib_lib} {yaml_lib})")

        # 5) Fix OHOS SDK bug: <mtd/ubi-user.h> has __packed redefinition errors
        #    OHOS has no UBI subsystem — provide minimal stubs via macro
        src_uboot = os.path.join(self.source_folder, "src", "uboot_env.c")
        replace_in_file(self, src_uboot,
                        "#include <mtd/ubi-user.h>",
                        "#if !defined(__OHOS__)\n#include <mtd/ubi-user.h>\n#else\n/* OHOS: no UBI subsystem */\n#define UBI_MAX_VOLUME 128\n#define UBI_IOCATT 0x40000001\n#define UBI_IOCVOLUP 0x40000002\n#define UBI_DEV_NUM_AUTO -1\nstruct ubi_attach_req { int ubi_num; int mtd_num; int vid_hdr_offset; };\nstruct ubi_mkvol_req { int vol_id; int align; long long bytes; int vol_type; char name[128]; };\nstruct ubi_rsvol_req { int vol_id; long long bytes; };\n#endif")

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSES/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["ubootenv"]
