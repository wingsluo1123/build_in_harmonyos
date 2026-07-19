#!/usr/bin/env python3
"""Conan recipe — i686-elf-gcc 13.3.0 (cross-GCC for i686-elf target).

Cross-compiled GCC running on aarch64-ohos, generating i686-elf binaries.
Built with in-tree GMP/MPFR/MPC/ISL prerequisites (downloaded by
_download_prerequisites from conandata.yml) and out-of-tree build.

R33: No hardcoded absolute paths — all prerequisites are downloaded
into the source tree and discovered automatically by GCC configure.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

import os
import shutil


class I686ElfGccConan(ConanFile):
    name = "i686-elf-gcc"
    version = "13.3.0"
    description = "GNU GCC cross-compiler for i686-elf target"
    license = "GPL-3.0-or-later WITH GCC-exception-3.1"
    homepage = "https://gcc.gnu.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _download_prerequisites(self):
        """Download and extract GMP/MPFR/MPC/ISL into the source tree.

        GCC configure will automatically discover these in-tree
        prerequisites via symlinks (gmp/, mpfr/, mpc/, isl/) without
        needing --with-gmp/--with-mpfr/--with-mpc configure options.
        """
        src = self.source_folder
        prereqs = self.conan_data.get("prerequisites", {})
        for name, info in prereqs.items():
            url = info["url"]
            sha256 = info.get("sha256", "")
            dirname = info["dirname"]
            # Download and extract (conan get() does both automatically)
            get(self, url, sha256=sha256 if sha256 else None,
                destination=src)
            # Create symlink (R5: rm -f && ln -s for HMDFS)
            link = os.path.join(src, name)
            if os.path.islink(link) or os.path.exists(link):
                os.remove(link)
            os.symlink(dirname, link)

    def _fix_configure_scripts(self):
        """Fix umask 077 -> 022 in all configure scripts (HMDFS issue)."""
        src = self.source_folder
        for root, dirs, files in os.walk(src):
            if "/build" in root or "/.git" in root:
                continue
            for f in files:
                if f in ("configure", "config.status"):
                    fpath = os.path.join(root, f)
                    try:
                        with open(fpath, "r") as fh:
                            content = fh.read()
                        if "umask 077" in content:
                            content = content.replace("umask 077", "umask 022")
                            with open(fpath, "w") as fh:
                                fh.write(content)
                    except Exception:
                        pass

    def _fix_libiberty_config_in(self):
        """Fix missing HAVE_* macros in libiberty/config.in template."""
        src = self.source_folder
        config_in = os.path.join(src, "libiberty", "config.in")
        if not os.path.exists(config_in):
            return
        with open(config_in, "r") as f:
            content = f.read()
        fixes = {
            "#undef HAVE_LIMITS_H": "#define HAVE_LIMITS_H 1",
            "#undef HAVE_SPAWN_H": "#define HAVE_SPAWN_H 1",
            "#undef HAVE_FCNTL_H": "#define HAVE_FCNTL_H 1",
            "#undef HAVE_SYS_MMAN_H": "#define HAVE_SYS_MMAN_H 1",
            "#undef HAVE_SYS_PARAM_H": "#define HAVE_SYS_PARAM_H 1",
            "#undef HAVE_SYS_TIME_H": "#define HAVE_SYS_TIME_H 1",
            "#undef HAVE_TIME_H": "#define HAVE_TIME_H 1",
            "#undef HAVE_SYS_RESOURCE_H": "#define HAVE_SYS_RESOURCE_H 1",
            "#undef HAVE_SYS_FILE_H": "#define HAVE_SYS_FILE_H 1",
            "#undef HAVE_SYS_PRCTL_H": "#define HAVE_SYS_PRCTL_H 1",
            "#undef HAVE_MALLOC_H": "#define HAVE_MALLOC_H 1",
        }
        for old, new in fixes.items():
            content = content.replace(old, new)
        with open(config_in, "w") as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)

        # R33: Download in-tree prerequisites (GMP/MPFR/MPC/ISL) from
        # conandata.yml instead of relying on system-installed libraries.
        # GCC configure auto-discovers gmp/, mpfr/, mpc/, isl/ symlinks
        # in the source tree — no hardcoded --with-gmp etc. paths.
        self._download_prerequisites()

        # Fix platform-specific issues
        self._fix_configure_scripts()
        self._fix_libiberty_config_in()

        # Out-of-tree build (R1: minimal parameters, --prefix=/ for conan)
        src = self.source_folder
        build_dir = os.path.join(self.build_folder, "gcc-build")
        os.makedirs(build_dir, exist_ok=True)

        _bash = shutil.which("bash") or "bash"
        _cc = shutil.which("clang") or "clang"
        _cxx = shutil.which("clang++") or "clang++"

        # R26: Set TMPDIR to writable path (OHOS /tmp is read-only, E002)
        # This enables make jobserver (needs writable tmp for pipe fds)
        _tmpdir = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(_tmpdir, exist_ok=True)

        env_prefix = (
            f"CONFIG_SHELL={_bash} SHELL={_bash} "
            f"CC={_cc} CXX={_cxx} "
            f"AR=llvm-ar RANLIB=llvm-ranlib NM=llvm-nm STRIP=llvm-strip "
            f"CPPFLAGS='' "
            f"CFLAGS='-fPIC -O2' CXXFLAGS='-fPIC -O2' "
            f"TMPDIR={_tmpdir} "
        )

        # Configure from build directory (out-of-tree)
        # No --with-gmp/--with-mpfr/--with-mpc: GCC auto-discovers
        # in-tree prerequisites downloaded by _download_prerequisites().
        self.run(
            f"{env_prefix} {src}/configure "
            f"--target=i686-elf "
            f"--build=aarch64-unknown-linux-gnu "
            f"--host=aarch64-unknown-linux-gnu "
            f"--prefix=/ "
            f"--without-headers "
            f"--enable-languages=c,c++ "
            f"--disable-nls --disable-werror --disable-multilib "
            f"--disable-libssp --disable-libquadmath --disable-libgomp "
            f"--disable-plugin "
            f"--disable-libstdc++-v3 "
            f"--with-gnu-as --with-gnu-ld",
            cwd=build_dir,
        )

        # Build with -j8 (mkfifo not supported on OHOS but make falls back
        # to parallel exec without jobserver coordination — still works)
        self.run(f"{env_prefix} make -j8", cwd=build_dir)

    def package(self):
        build_dir = os.path.join(self.build_folder, "gcc-build")

        _bash = shutil.which("bash") or "bash"

        # Install to package directory (DESTDIR = self.package_folder)
        self.run(
            f"CONFIG_SHELL={_bash} SHELL={_bash} "
            f"make install DESTDIR={self.package_folder}",
            cwd=build_dir,
        )

    def package_info(self):
        # GCC is a command-line tool — declare bindirs
        self.cpp_info.bindirs = ["bin"]
        # No libs to link against (cross-compiler application)
        self.cpp_info.libs = []
