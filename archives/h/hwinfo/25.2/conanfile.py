#!/usr/bin/env python3
"""Conan recipe for hwinfo 25.2 — hardware information tool (openSUSE).

Build system: Makefile (no configure script).
Products: hwinfo binary, libhd.a (static), libhd.so.25.2 (shared),
          hd.h (header), hwinfo.pc (pkg-config).

Platform adaptations:
  1. ohos_fixup.h: prevent sockaddr_storage redefinition (OHOS sysroot bug)
  2. version.h: generated via patch (git2log needs .git which is absent)
  3. ISDN.CDB.txt: copied instead of symlinked (HMDFS ln -s hang)
  4. lex→flex: flex is available as /data/service/hnp/bin/flex
  5. Pre-generated hd_ids.h/hd_ids_tiny.h/hd.ids: check_hd on 186K-line PCI
     data takes ~15 min; pre-generated patches skip this, reducing build to ~2 min.
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

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("uuid/2.40.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        src = self.conan_data["sources"]
        get(self, **src, filename="hwinfo-25.2.tar.xz", strip_root=True)

    def build(self):
        # Apply patches: version.h + pre-generated hd_ids.h/hd_ids_tiny.h/hd.ids
        apply_conandata_patches(self)

        src = self.source_folder

        # --- Disable check_hd rules in src/ids/Makefile ---
        # Pre-generated files are already applied via patches.
        # Without this, make would rebuild them via check_hd (takes ~15 min).
        ids_dir = os.path.join(src, "src", "ids")
        ids_makefile = os.path.join(ids_dir, "Makefile")
        if os.path.exists(ids_makefile):
            with open(ids_makefile, "r") as mf:
                mk = mf.read()
            # Add check_hd to TARGETS so it gets built (needed by install target)
            mk = mk.replace(
                "TARGETS = $(LIBHD_D)",
                "TARGETS = $(LIBHD_D) check_hd"
            )
            # Replace the hd_ids.h regeneration rule with no-op (pre-generated)
            mk = mk.replace(
                "hd_ids.h hd.ids: check_hd $(IDFILES)\n"
                "\t./check_hd --check --sort --cfile hd_ids.h $(IDFILES)",
                "hd_ids.h hd.ids:\n\t@true"
            )
            mk = mk.replace(
                "hd_ids_tiny.h: check_hd hd.ids\n"
                "\t./check_hd --mini --cfile hd_ids_tiny.h --log=hd_tiny.log --out=hd_tiny.ids hd.ids",
                "hd_ids_tiny.h:\n\t@true"
            )
            with open(ids_makefile, "w") as mf:
                mf.write(mk)

        # --- Platform fix 1: ohos_fixup.h ---
        fixup_path = os.path.join(src, "ohos_fixup.h")
        with open(fixup_path, "w") as f:
            f.write(
                "#ifndef _OHOS_FIXUP_H\n"
                "#define _OHOS_FIXUP_H\n"
                "#define _UAPI_LINUX_SOCKET_H\n"
                "typedef unsigned short __kernel_sa_family_t;\n"
                "#endif\n"
            )

        # --- Platform fix 2: ISDN.CDB.txt (avoid HMDFS ln -s hang) ---
        cdb_dir = os.path.join(src, "src", "isdn", "cdb")
        cdb_txt = os.path.join(cdb_dir, "ISDN.CDB.txt")
        if not os.path.exists(cdb_txt):
            src_txt = os.path.join(cdb_dir, "ISDN.ppc.txt")
            if os.path.exists(src_txt):
                shutil.copy2(src_txt, cdb_txt)

        # --- Platform fix 3: lex → flex ---
        local_bin = os.path.join(src, ".local_bin")
        os.makedirs(local_bin, exist_ok=True)
        lex_link = os.path.join(local_bin, "lex")
        if not os.path.exists(lex_link):
            flex_path = shutil.which("flex") or "/data/service/hnp/bin/flex"
            if os.path.exists(flex_path):
                os.symlink(flex_path, lex_link)

        # --- Build environment ---
        # R33: Get compiler from Conan conf, not from shell env vars
        uuid_root = str(self.dependencies["uuid"].package_folder)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar") or "llvm-ar"
        ranlib = compilers.get("ranlib") or "llvm-ranlib"

        os.environ["CC"] = cc
        os.environ["AR"] = ar
        os.environ["RANLIB"] = ranlib
        os.environ["CFLAGS"] = f"-fPIC -O2 -I{uuid_root}/include -include {fixup_path}"
        os.environ["LDFLAGS"] = f"-L{uuid_root}/lib"
        os.environ["SO_LIBS"] = "-luuid"
        os.environ["PATH"] = f"{local_bin}:{os.environ.get('PATH', '')}"

        # R9: use -j1
        self.run("make -j1", cwd=src)

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        # Build check_hd (needed by install target, not built during make -j1
        # because the hd_ids.h regeneration rule was disabled)
        ids_dir = os.path.join(src, "src", "ids")
        check_hd = os.path.join(ids_dir, "check_hd")
        if not os.path.exists(check_hd):
            cc = os.environ.get("CC", "clang")
            cflags = os.environ.get("CFLAGS", "-fPIC -O2")
            self.run(f"{cc} {cflags} -I../../src/hd check_hd.c -o check_hd", cwd=ids_dir)

        self.run(
            f"make install DESTDIR={pkg} INSTALL_PREFIX=/usr",
            cwd=src,
        )

        # Move sbin → bin (conan convention)
        sbin_dir = os.path.join(pkg, "usr", "sbin")
        bin_dir = os.path.join(pkg, "bin")
        if os.path.isdir(sbin_dir):
            os.makedirs(bin_dir, exist_ok=True)
            for f in os.listdir(sbin_dir):
                shutil.move(os.path.join(sbin_dir, f), os.path.join(bin_dir, f))
            shutil.rmtree(os.path.join(pkg, "usr", "sbin"))

        # Move lib, include, share to package root
        for d in ["lib", "include", "share"]:
            src_d = os.path.join(pkg, "usr", d)
            dst_d = os.path.join(pkg, d)
            if os.path.isdir(src_d):
                if os.path.isdir(dst_d):
                    for f in os.listdir(src_d):
                        shutil.move(os.path.join(src_d, f), os.path.join(dst_d, f))
                    shutil.rmtree(src_d)
                else:
                    shutil.move(src_d, dst_d)

        usr_dir = os.path.join(pkg, "usr")
        if os.path.isdir(usr_dir):
            shutil.rmtree(usr_dir, ignore_errors=True)

        copy(self, "COPYING", src, os.path.join(pkg, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["hd"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "hwinfo")
