#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Btrfsprogs, btrfs-progs, 5.19.1, Btrfs 文件系统工具集，包括 mkfs.btrfs、btrfs、btrfsck 等命令, MIT, https://btrfs.readthedocs.io/
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class BtrfsprogsConan(ConanFile):
    name = "btrfs-progs"
    version = "5.19.1"
    description = "Btrfs 文件系统工具集，包括 mkfs.btrfs、btrfs、btrfsck 等命令"
    license = "MIT"
    homepage = "https://btrfs.readthedocs.io/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        # Fix missing time.h on OHOS (struct tm not found in multiple source files)
        tc.extra_cflags.append("-include time.h")
        # btrfs-progs specific configure args
        tc.configure_args.append("--disable-documentation")
        tc.configure_args.append("--disable-libudev")
        tc.configure_args.append("--disable-python")
        tc.configure_args.append("--disable-lzo")
        tc.configure_args.append("--disable-zstd")
        tc.configure_args.append("--disable-convert")
        tc.generate()
        # E001: Set CC/CXX for autotools on OHOS
        env = Environment()
        env.define("CC", "clang")
        env.define("CXX", "clang++")
        env.define("AWK", "/data/service/hnp/bin/awk")
        # Add colrm pkg-config path for blkid, uuid, etc.
        colrm_pc = "/data/service/hnp/colrm.org/colrm_1.1/lib/pkgconfig"
        custom_pc = os.path.expanduser("~/tmp/pkgconfig")
        existing_pc = os.environ.get("PKG_CONFIG_PATH", "")
        # Custom pc first so uuid.pc with correct include path takes precedence
        pc_paths = custom_pc + ":" + colrm_pc
        if existing_pc:
            pc_paths += ":" + existing_pc
        env.define("PKG_CONFIG_PATH", pc_paths)
        # Set TMPDIR to writable+executable directory (config.status needs to exec awk scripts)
        env.define("TMPDIR", os.path.expanduser("~/tmp"))
        # Provide zlib for configure (no pkg-config file on OHOS)
        sysroot = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr"
        env.define("ZLIB_CFLAGS", f"-I{sysroot}/include")
        env.define("ZLIB_LIBS", f"-L{sysroot}/lib/aarch64-linux-ohos -lz")
        env.vars(self, scope="build").save_script("conanbuild_env")

    def build(self):
        apply_conandata_patches(self)
        # E007: Fix config.guess/config.sub for OHOS
        skill_root = os.environ.get("SKILL_ROOT", "/storage/Users/currentUser/.opendesk/apps/skills/resources/build_in_harmonyos")
        # patch-autotools-ohos.pl requires both config.guess and config.sub as arguments
        for subdir in ["", "config", "build-aux", "autotools"]:
            cg = os.path.join(self.source_folder, subdir, "config.guess") if subdir else os.path.join(self.source_folder, "config.guess")
            cs = os.path.join(self.source_folder, subdir, "config.sub") if subdir else os.path.join(self.source_folder, "config.sub")
            if os.path.exists(cg) and os.path.exists(cs):
                self.run(f'perl {skill_root}/scripts/patch-autotools-ohos.pl {cg} {cs}', cwd=self.source_folder)
        # Fix config.status permission issue: umask 077 creates too-restrictive dirs on OHOS
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            self.run(f"sed -i 's/umask 077/umask 022/g' {configure_path}", cwd=self.source_folder)
        # Fix missing #include <time.h> (struct tm not found on OHOS)
        for src_file in ["kernel-shared/print-tree.c", "common/format-output.c"]:
            fpath = os.path.join(self.source_folder, src_file)
            if os.path.exists(fpath):
                self.run(f"sed -i '/#include <stdio.h>/a #include <time.h>' {fpath}", cwd=self.source_folder)
        # Create symlinks for headers that Make dep tracking needs as relative paths
        custom_include = os.path.expanduser("~/tmp/uuid_include")
        for hdr_dir in ["uuid", "blkid"]:
            src_hdr = os.path.join(custom_include, hdr_dir, f"{hdr_dir}.h")
            dst_dir = os.path.join(self.source_folder, hdr_dir)
            dst_hdr = os.path.join(dst_dir, f"{hdr_dir}.h")
            if os.path.exists(src_hdr) and not os.path.exists(dst_hdr):
                os.makedirs(dst_dir, exist_ok=True)
                os.symlink(src_hdr, dst_hdr)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
