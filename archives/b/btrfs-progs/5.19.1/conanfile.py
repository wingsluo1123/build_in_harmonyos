#!/usr/bin/env python3
"""Conan recipe for btrfs-progs 5.19.1 — Btrfs filesystem utilities.

Builds btrfs-progs with ALL features enabled (convert, lzo, zstd, libudev).
Dependencies not available in the Conan repo (blkid, lzo2, e2fsprogs/ext2fs)
are built from source within this recipe to avoid feature trimming.

Platform adaptations:
  - E011: Fix umask 077 → 022 for HMDFS compatibility
  - E051: Add pthread stubs for missing pthread_cancel etc. on OHOS/musl
  - Fix LN_S for HMDFS (no hard links)
  - Add include paths via EXTRA_CFLAGS for non-standard dependency locations
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BtrfsProgsConan(ConanFile):
    name = "btrfs-progs"
    version = "5.19.1"
    description = "Btrfs filesystem utilities: mkfs.btrfs, btrfs, btrfsck, btrfs-convert, etc."
    license = "GPL-2.0-only"
    homepage = "https://btrfs.readthedocs.io/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        self.requires("uuid/2.40.1")
        self.requires("zstd/1.5.7")
        self.requires("zlib/1.3.1")
        self.requires("libudev-zero/1.0.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-documentation",
            "--disable-python",
            "--enable-convert",
            "--enable-lzo",
            "--enable-zstd",
            "--enable-libudev",
            "--enable-programs",
            "--enable-shared",
            "--enable-static",
            "--with-crypto=builtin",
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
        ])
        tc.generate()

    def _fix_umask_in_configure(self, src_dir):
        """Fix E011: umask 077 → 022 in configure and config.status for HMDFS.

        The configure script generates config.status with umask 077 which
        fails on HMDFS filesystem. Patch configure BEFORE running it so the
        generated config.status also uses umask 022.
        """
        configure_path = os.path.join(src_dir, "configure")
        if os.path.exists(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure_path, "w") as f:
                f.write(content)

        # Also fix config.status if it already exists (from a previous configure run)
        config_status = os.path.join(src_dir, "config.status")
        if os.path.exists(config_status):
            with open(config_status, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(config_status, "w") as f:
                f.write(content)
            self.run(f"cd {src_dir} && ./config.status", env="conanbuild")

    def _build_blkid(self, deps_prefix):
        """Build libblkid from util-linux source (not available as Conan package)."""
        util_linux_src = os.path.join(self.build_folder, "util-linux-src")
        get(self, **self.conan_data["util_linux_sources"],
            destination=util_linux_src, strip_root=True)

        tmpdir = os.path.join(util_linux_src, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir

        # Fix E011 umask BEFORE running configure
        self._fix_umask_in_configure(util_linux_src)

        self.run(f"cd {util_linux_src} && ./configure "
                 f"--prefix={deps_prefix} "
                 f"--enable-libblkid --disable-all-programs "
                 f"--without-python --disable-makeinstall-chown "
                 f"--disable-makeinstall-setuid "
                 f"--enable-static --disable-shared "
                 f"AWK=awk "
                 f"--build=aarch64-unknown-linux-gnu "
                 f"--host=aarch64-unknown-linux-gnu", env="conanbuild")

        self.run(f"cd {util_linux_src} && make -j1", env="conanbuild")

        # Install libblkid manually
        for subdir in ["lib", "include/blkid", "lib/pkgconfig"]:
            os.makedirs(os.path.join(deps_prefix, subdir), exist_ok=True)

        libblkid_a = os.path.join(util_linux_src, ".libs", "libblkid.a")
        if os.path.exists(libblkid_a):
            shutil.copy2(libblkid_a, os.path.join(deps_prefix, "lib"))
        blkid_pc = os.path.join(util_linux_src, "libblkid", "blkid.pc")
        if os.path.exists(blkid_pc):
            shutil.copy2(blkid_pc, os.path.join(deps_prefix, "lib", "pkgconfig"))
        blkid_h = os.path.join(util_linux_src, "libblkid", "src", "blkid.h")
        if os.path.exists(blkid_h):
            shutil.copy2(blkid_h, os.path.join(deps_prefix, "include", "blkid"))

    def _build_lzo(self, deps_prefix):
        """Build lzo2 from source (not available as Conan package)."""
        lzo_src = os.path.join(self.build_folder, "lzo-src")
        get(self, **self.conan_data["lzo_sources"],
            destination=lzo_src, strip_root=True)

        tmpdir = os.path.join(lzo_src, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir

        # Fix E011 umask BEFORE running configure
        self._fix_umask_in_configure(lzo_src)

        self.run(f"cd {lzo_src} && ./configure "
                 f"--prefix={deps_prefix} "
                 f"--enable-static --disable-shared "
                 f"--build=aarch64-unknown-linux-gnu "
                 f"--host=aarch64-unknown-linux-gnu", env="conanbuild")

        self.run(f"cd {lzo_src} && make -j1 && make install", env="conanbuild")

    def _build_e2fsprogs(self, deps_prefix):
        """Build libext2fs and libcom_err from e2fsprogs source."""
        e2fs_src = os.path.join(self.build_folder, "e2fsprogs-src")
        get(self, **self.conan_data["e2fsprogs_sources"],
            destination=e2fs_src, strip_root=True)

        tmpdir = os.path.join(e2fs_src, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir

        # Fix E011 umask BEFORE running configure
        self._fix_umask_in_configure(e2fs_src)

        self.run(f"cd {e2fs_src} && ./configure "
                 f"--prefix={deps_prefix} "
                 f"--enable-static --disable-shared "
                 f"--build=aarch64-unknown-linux-gnu "
                 f"--host=aarch64-unknown-linux-gnu", env="conanbuild")

        # Build only libraries (not tools) to avoid fsmap linking issues
        for libdir in ["lib/et", "lib/ext2fs", "lib/e2p"]:
            lib_path = os.path.join(e2fs_src, libdir)
            if os.path.isdir(lib_path):
                self.run(f"cd {e2fs_src} && make -C {libdir} -j1 LN='cp -f'",
                         env="conanbuild")

        # Install libraries and headers manually
        for subdir in ["lib", "include/ext2fs", "include/et", "lib/pkgconfig"]:
            os.makedirs(os.path.join(deps_prefix, subdir), exist_ok=True)

        for lib in ["lib/ext2fs/libext2fs.a", "lib/et/libcom_err.a",
                    "lib/e2p/libe2p.a"]:
            src = os.path.join(e2fs_src, lib)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(deps_prefix, "lib"))

        ext2fs_dir = os.path.join(e2fs_src, "lib", "ext2fs")
        if os.path.isdir(ext2fs_dir):
            for hdr in os.listdir(ext2fs_dir):
                if hdr.endswith(".h"):
                    shutil.copy2(os.path.join(ext2fs_dir, hdr),
                                 os.path.join(deps_prefix, "include", "ext2fs"))

        com_err_h = os.path.join(e2fs_src, "lib", "et", "com_err.h")
        if os.path.exists(com_err_h):
            shutil.copy2(com_err_h, os.path.join(deps_prefix, "include", "et"))

        # Create pkg-config files
        with open(os.path.join(deps_prefix, "lib", "pkgconfig", "ext2fs.pc"), "w") as f:
            f.write(
                f"prefix={deps_prefix}\n"
                f"exec_prefix=${{prefix}}\n"
                f"libdir=${{exec_prefix}}/lib\n"
                f"includedir=${{prefix}}/include\n\n"
                f"Name: ext2fs\n"
                f"Description: Ext2 filesystem library\n"
                f"Version: 1.47.1\n"
                f"Cflags: -I${{includedir}}/ext2fs\n"
                f"Libs: -L${{libdir}} -lext2fs\n"
                f"Libs.private: -lcom_err\n"
            )
        with open(os.path.join(deps_prefix, "lib", "pkgconfig", "com_err.pc"), "w") as f:
            f.write(
                f"prefix={deps_prefix}\n"
                f"exec_prefix=${{prefix}}\n"
                f"libdir=${{exec_prefix}}/lib\n"
                f"includedir=${{prefix}}/include\n\n"
                f"Name: com_err\n"
                f"Description: Common error handling library\n"
                f"Version: 1.47.1\n"
                f"Cflags: -I${{includedir}}/et\n"
                f"Libs: -L${{libdir}} -lcom_err\n"
            )

    def _setup_env_for_configure(self, deps_prefix):
        """Set up environment variables for btrfs-progs configure."""
        # Collect pkg-config paths from conan deps
        pkg_config_paths = [os.path.join(deps_prefix, "lib", "pkgconfig")]
        for dep_name in ["uuid", "zstd", "zlib", "libudev-zero"]:
            dep = self.dependencies[dep_name]
            try:
                pkg_folder = str(dep.package_folder)
                for dirpath, _, files in os.walk(pkg_folder):
                    if any(f.endswith(".pc") for f in files):
                        pkg_config_paths.append(dirpath)
            except Exception:
                pass

        # Fix pkg-config files in conan cache
        for pc_dir in pkg_config_paths:
            if not os.path.isdir(pc_dir):
                continue
            for pc_file in os.listdir(pc_dir):
                if not pc_file.endswith(".pc"):
                    continue
                pc_path = os.path.join(pc_dir, pc_file)
                try:
                    with open(pc_path, "r") as f:
                        content = f.read()
                    changed = False
                    if "prefix=/usr/local" in content:
                        content = content.replace("prefix=/usr/local",
                                                  f"prefix={pc_dir}/..")
                        changed = True
                    if content.startswith("prefix=/\n"):
                        content = content.replace("prefix=/\n",
                                                  f"prefix={pc_dir}/..\n", 1)
                        content = content.replace("libdir=//lib",
                                                  "libdir=${exec_prefix}/lib")
                        content = content.replace("includedir=//include",
                                                  "includedir=${prefix}/include")
                        changed = True
                    if changed:
                        with open(pc_path, "w") as f:
                            f.write(content)
                except Exception:
                    pass

        os.environ["PKG_CONFIG_PATH"] = ":".join(pkg_config_paths)
        os.environ["TMPDIR"] = os.environ.get("TMPDIR", "/tmp")

        # Also set LDFLAGS and CFLAGS for deps that don't use pkg-config (like lzo2)
        deps_lib = os.path.join(deps_prefix, "lib")
        deps_inc = os.path.join(deps_prefix, "include")
        existing_ldflags = os.environ.get("LDFLAGS", "")
        os.environ["LDFLAGS"] = f"{existing_ldflags} -L{deps_lib}".strip()
        existing_cflags = os.environ.get("CFLAGS", "")
        os.environ["CFLAGS"] = f"{existing_cflags} -I{deps_inc}".strip()
        existing_cppflags = os.environ.get("CPPFLAGS", "")
        os.environ["CPPFLAGS"] = f"{existing_cppflags} -I{deps_inc}".strip()

    def build(self):
        # Build missing dependencies from source
        deps_prefix = os.path.join(self.build_folder, "deps_prefix")
        os.makedirs(deps_prefix, exist_ok=True)

        self._build_blkid(deps_prefix)
        self._build_lzo(deps_prefix)
        self._build_e2fsprogs(deps_prefix)

        # Set up environment for configure
        self._setup_env_for_configure(deps_prefix)

        # Apply patches (umask fix, pthread stubs)
        apply_conandata_patches(self)

        # Fix E011: umask 077 → 022 in configure
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure_path, "w") as f:
                f.write(content)

        # Compile pthread stubs - create file directly (more reliable than patch)
        pthread_stubs_path = os.path.join(self.source_folder, "pthread-stubs.c")
        with open(pthread_stubs_path, "w") as f:
            f.write("""/* pthread-stubs.c - Stub implementations for OHOS/musl */
#include <pthread.h>
#include <errno.h>

__attribute__((used))
int pthread_cancel(pthread_t thread) { (void)thread; return 0; }

__attribute__((used))
int pthread_setcancelstate(int state, int *oldstate) {
    (void)state; if (oldstate) *oldstate = PTHREAD_CANCEL_ENABLE; return 0;
}

__attribute__((used))
int pthread_setcanceltype(int type, int *oldtype) {
    (void)type; if (oldtype) *oldtype = PTHREAD_CANCEL_DEFERRED; return 0;
}

__attribute__((used))
int pthread_tryjoin_np(pthread_t thread, void **retval) {
    (void)thread; if (retval) *retval = NULL; return EBUSY;
}
""")
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        pthread_stubs_o = os.path.join(self.source_folder, "pthread-stubs.o")
        self.run(f"{cc} -c -fPIC -O2 -o {pthread_stubs_o} {pthread_stubs_path}")

        # Run configure in the source folder (where Makefile is)
        prefix = self.package_folder if self.package_folder else "/usr/local"
        configure_cmd = (
            f"./configure "
            f"--prefix={prefix} "
            f"--disable-documentation "
            f"--disable-python "
            f"--enable-convert "
            f"--enable-lzo "
            f"--enable-zstd "
            f"--enable-libudev "
            f"--enable-programs "
            f"--enable-shared "
            f"--enable-static "
            f"--with-crypto=builtin "
            f"--build=aarch64-unknown-linux-gnu "
            f"--host=aarch64-unknown-linux-gnu"
        )
        self.run(configure_cmd, cwd=self.source_folder, env="conanbuild")

        # Fix Makefile AFTER configure (add include paths, fix LN_S, add pthread-stubs.o)
        makefile_path = os.path.join(self.source_folder, "Makefile")
        if os.path.exists(makefile_path):
            with open(makefile_path, "r") as f:
                content = f.read()

            extra_includes = [f"-I{deps_prefix}/include"]
            for dep_name in ["uuid", "zstd", "zlib", "libudev-zero"]:
                dep = self.dependencies[dep_name]
                try:
                    pkg_folder = str(dep.package_folder)
                    include_dir = os.path.join(pkg_folder, "include")
                    if os.path.isdir(include_dir):
                        extra_includes.append(f"-I{include_dir}")
                except Exception:
                    pass

            content = content.replace(
                "EXTRA_CFLAGS :=",
                f"EXTRA_CFLAGS := {' '.join(extra_includes)}"
            )
            content = content.replace("LN_S = ln -s", "LN_S = cp -f")
            content = content.replace(
                "kernel-shared/zoned.o\t\\",
                "kernel-shared/zoned.o\t\\\n\tpthread-stubs.o\t\\"
            )

            with open(makefile_path, "w") as f:
                f.write(content)

        # Run make in the source folder
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        self.run("make install", cwd=self.source_folder, env="conanbuild")

    def package_info(self):
        self.cpp_info.libs = ["btrfs", "btrfsutil"]
        self.cpp_info.includedirs = ["include/btrfs", "include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
