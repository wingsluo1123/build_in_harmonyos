#!/usr/bin/env python3
"""Conan recipe for hwinfo 25.2 — hardware information tool from openSUSE.

Build system: Makefile (no configure script).
Dependencies: uuid/2.40.1 (libuuid from util-linux, for smbios.c).

Key adaptation issues:
  1. version.h not auto-generated (git2log requires .git dir) → generated in build()
  2. sockaddr_storage redefinition (OHOS sys/socket.h vs linux/socket.h) → -D__MUSL__
  3. lex command missing → use flex via wrapper
  4. ln -s hangs on HMDFS in cdb Makefile → pre-create ISDN.CDB.txt by copy
  5. GNU install command missing on OHOS → use conan copy() in package()
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class HwinfoConan(ConanFile):
    name = "hwinfo"
    version = "25.2"
    description = "Hardware information tool from openSUSE"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/openSUSE/hwinfo"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("uuid/2.40.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, NEVER from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")

        # Get uuid dependency paths
        uuid_pkg = str(self.dependencies["uuid"].package_folder)
        uuid_inc = os.path.join(uuid_pkg, "include")
        uuid_lib = os.path.join(uuid_pkg, "lib")

        version = str(self.version)

        # 1. Generate version.h (Makefile's git2log fails without .git dir)
        version_h = os.path.join(self.source_folder, "src", "hd", "version.h")
        with open(version_h, "w") as f:
            f.write(f'#define HD_VERSION_STRING "{version}"\n')

        # 2. Pre-create ISDN.CDB.txt by copy (ln -s hangs on HMDFS)
        cdb_dir = os.path.join(self.source_folder, "src", "isdn", "cdb")
        cdb_txt = os.path.join(cdb_dir, "ISDN.CDB.txt")
        if not os.path.exists(cdb_txt) or os.path.islink(cdb_txt):
            if os.path.islink(cdb_txt):
                os.unlink(cdb_txt)
            shutil.copy(os.path.join(cdb_dir, "ISDN.ppc.txt"), cdb_txt)

        # 3. Pre-generate lex.yy.c (flex, not lex)
        lex_yy = os.path.join(cdb_dir, "lex.yy.c")
        if not os.path.exists(lex_yy):
            self.run(f"flex -o {lex_yy} {os.path.join(cdb_dir, 'isdn_cdb.lex')}")

        # 4. Build isdn_cdb tool and generate isdn_cdb.h
        isdn_cdb_h = os.path.join(cdb_dir, "isdn_cdb.h")
        # cflags for cdb tools (defined outside if to avoid NameError if files already exist)
        cflags = f"-O2 -Wall -Wno-pointer-sign -pipe -g -fPIC -I{uuid_inc} -D__MUSL__ -I{os.path.join(self.source_folder, 'src', 'hd')}"
        if not os.path.exists(isdn_cdb_h):
            self.run(f"{cc} -c {cflags} {os.path.join(cdb_dir, 'isdn_cdb.c')} -o {os.path.join(cdb_dir, 'isdn_cdb.o')}")
            self.run(f"{cc} -c {cflags} {os.path.join(cdb_dir, 'cdb_read.c')} -o {os.path.join(cdb_dir, 'cdb_read.o')}")
            self.run(f"{cc} {os.path.join(cdb_dir, 'isdn_cdb.o')} {os.path.join(cdb_dir, 'cdb_read.o')} -o {os.path.join(cdb_dir, 'isdn_cdb')}")
            self.run(f"{os.path.join(cdb_dir, 'isdn_cdb')} {cdb_txt} {isdn_cdb_h}")

        # 5. Build mk_isdnhwdb and generate ISDN.CDB.hwdb
        hwdb_file = os.path.join(cdb_dir, "ISDN.CDB.hwdb")
        if not os.path.exists(hwdb_file):
            self.run(f"{cc} -c {cflags} {os.path.join(cdb_dir, 'mk_isdnhwdb.c')} -o {os.path.join(cdb_dir, 'mk_isdnhwdb.o')}")
            self.run(f"{cc} {os.path.join(cdb_dir, 'mk_isdnhwdb.o')} {os.path.join(cdb_dir, 'cdb_read.o')} -o {os.path.join(cdb_dir, 'mk_isdnhwdb')}")
            self.run(f"{os.path.join(cdb_dir, 'mk_isdnhwdb')} {cdb_txt} {hwdb_file}")

        # 6. Build hwinfo with make
        # -D__MUSL__ fixes sockaddr_storage redefinition (OHOS sys/socket.h vs linux/socket.h)
        # Use EXTRA_FLAGS instead of CFLAGS to preserve Makefile.common's include paths
        # R9: Always use -j1
        extra_flags = f"-I{uuid_inc} -D__MUSL__"
        ldflags = f"-L{uuid_lib} -Lsrc"  # include -Lsrc (Makefile.common's += is overridden)

        shared_flags = "" if not self.options.shared else "-fPIC -fvisibility=hidden"
        libs = "-lhd -luuid"  # both static and shared need -luuid (smbios.c uses uuid_unparse_lower)
        self.run(
            f'make CC={cc} '
            f'EXTRA_FLAGS="{extra_flags}" '
            f'LDFLAGS="{ldflags}" '
            f'SHARED_FLAGS="{shared_flags}" '
            f'LIBS="{libs}" '
            f'HWINFO_VERSION={version} '
            f'-j1',
            cwd=self.source_folder
        )

    def package(self):
        # Copy headers
        copy(self, "hd.h", os.path.join(self.source_folder, "src", "hd"),
             os.path.join(self.package_folder, "include"))

        # Copy libraries
        if self.options.shared:
            copy(self, "libhd.so*", os.path.join(self.source_folder, "src"),
                 os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libhd.a", os.path.join(self.source_folder, "src"),
                 os.path.join(self.package_folder, "lib"))

        # Copy executables
        copy(self, "hwinfo", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "check_hd", os.path.join(self.source_folder, "src", "ids"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "convert_hd", os.path.join(self.source_folder, "src", "ids"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "getsysinfo", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "mk_isdnhwdb", os.path.join(self.source_folder, "src", "isdn", "cdb"),
             os.path.join(self.package_folder, "bin"))

        # Copy pkg-config file
        copy(self, "hwinfo.pc", self.source_folder,
             os.path.join(self.package_folder, "lib", "pkgconfig"))

        # Copy data files
        cdb_dir = os.path.join(self.source_folder, "src", "isdn", "cdb")
        copy(self, "ISDN.CDB.txt", cdb_dir,
             os.path.join(self.package_folder, "share", "hwinfo"))
        copy(self, "ISDN.CDB.hwdb", cdb_dir,
             os.path.join(self.package_folder, "share", "hwinfo"))

    def package_info(self):
        self.cpp_info.libs = ["hd"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "hwinfo")
        self.cpp_info.set_property("cmake_file_name", "hwinfo")
        self.cpp_info.set_property("cmake_target_name", "hwinfo::hd")
