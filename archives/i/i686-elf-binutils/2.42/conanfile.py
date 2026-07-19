#!/usr/bin/env python3
"""Conan recipe — i686-elf-binutils 2.42 (cross-binutils for i686-elf target).

Cross-compiled GNU Binutils running on aarch64-ohos, generating i686-elf binaries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment

import os
import shutil


class I686ElfBinutilsConan(ConanFile):
    name = "i686-elf-binutils"
    version = "2.42"
    description = "GNU Binutils cross-compiler tools for i686-elf target"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/binutils/"
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

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Cross-compilation: build on aarch64-ohos, target i686-elf
        tc.configure_args.append("--target=i686-elf")
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # Disable gprofng (uses Linux-specific SIGEV_THREAD_ID, not on OHOS)
        tc.configure_args.append("--disable-gprofng")
        # Disable NLS (no gettext)
        tc.configure_args.append("--disable-nls")
        # Disable werror (clang produces different warnings than gcc)
        tc.configure_args.append("--disable-werror")
        tc.generate()

        # Use LLVM toolchain and dynamic bash path
        _bash = shutil.which("bash") or "bash"
        env = Environment()
        env.define("CONFIG_SHELL", _bash)
        env.define("SHELL", _bash)
        env.define("AR", "llvm-ar")
        env.define("RANLIB", "llvm-ranlib")
        env.define("NM", "llvm-nm")
        env.define("STRIP", "llvm-strip")
        env.define("CPPFLAGS", "")
        envvars = env.vars(self, scope="build")
        envvars.save_script("env_override")

    def _build_env_prefix(self):
        """Build environment prefix string with dynamic tool paths."""
        _bash = shutil.which("bash") or "bash"
        _cc = shutil.which("clang") or "clang"
        _cxx = shutil.which("clang++") or "clang++"
        return (
            f"CONFIG_SHELL={_bash} SHELL={_bash} "
            f"CC={_cc} CXX={_cxx} "
            f"AR=llvm-ar RANLIB=llvm-ranlib NM=llvm-nm STRIP=llvm-strip "
            f"CPPFLAGS='' "
            f"CFLAGS='-fPIC -O2' CXXFLAGS='-fPIC -O2' "
        )

    def build(self):
        apply_conandata_patches(self)

        # Fix config.in template BEFORE configure/make: libiberty/configure
        # runs during make and regenerates config.h from config.in, overwriting
        # any post-configure fixes. OHOS cross-compile fails to detect standard
        # headers (limits.h etc.), so we pre-define them in the template.
        self._fix_libiberty_config_in()

        env_prefix = self._build_env_prefix()
        src = self.source_folder or "."
        self.run(f"{env_prefix} {src}/configure --target=i686-elf "
                 f"--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu "
                 f"--prefix=/ --disable-gprofng --disable-nls --disable-werror",
                 cwd=src)

        # Also fix any already-generated config.h as backup
        self._fix_config_h()

        self.run(f"{env_prefix} make -j2", cwd=src)

    def _fix_libiberty_config_in(self):
        """Fix libiberty/config.in template before configure runs.

        During make, libiberty/configure runs and generates config.h from
        config.in. OHOS cross-compile fails to detect standard headers
        (limits.h, spawn.h, etc.), causing errors like:
          fibheap.c: error: use of undeclared identifier 'LONG_MIN'

        By modifying config.in to #define these headers before configure,
        the generated config.h will have the correct defines.
        """
        from conan.tools.files import load
        for base in [self.source_folder, self.build_folder, "."]:
            config_in = os.path.join(base, "libiberty", "config.in")
            if os.path.exists(config_in):
                content = load(self, config_in)
                # Replace #undef with #define for headers that OHOS has but
                # autoconf cross-compile detection fails to find
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
                break

    def _fix_config_h(self):
        """Fix missing HAVE_* macros in libiberty/config.h after configure."""
        from conan.tools.files import load
        for base in [self.build_folder, self.source_folder]:
            config_h = os.path.join(base, "libiberty", "config.h")
            if os.path.exists(config_h):
                content = load(self, config_h)
                fixes = {
                    "/* #undef HAVE_LIMITS_H */": "#define HAVE_LIMITS_H 1",
                    "/* #undef HAVE_SPAWN_H */": "#define HAVE_SPAWN_H 1",
                    "/* #undef HAVE_FCNTL_H */": "#define HAVE_FCNTL_H 1",
                    "/* #undef HAVE_SYS_MMAN_H */": "#define HAVE_SYS_MMAN_H 1",
                    "/* #undef HAVE_SYS_PARAM_H */": "#define HAVE_SYS_PARAM_H 1",
                    "/* #undef HAVE_SYS_TIME_H */": "#define HAVE_SYS_TIME_H 1",
                    "/* #undef HAVE_TIME_H */": "#define HAVE_TIME_H 1",
                    "/* #undef HAVE_SYS_RESOURCE_H */": "#define HAVE_SYS_RESOURCE_H 1",
                    "/* #undef HAVE_SYS_FILE_H */": "#define HAVE_SYS_FILE_H 1",
                    "/* #undef HAVE_SYS_PRCTL_H */": "#define HAVE_SYS_PRCTL_H 1",
                    "/* #undef HAVE_MALLOC_H */": "#define HAVE_MALLOC_H 1",
                }
                for old, new in fixes.items():
                    content = content.replace(old, new)
                with open(config_h, "w") as f:
                    f.write(content)
                break

    def package(self):
        env_prefix = self._build_env_prefix()
        src = self.source_folder or "."
        self.run(f"{env_prefix} make install DESTDIR={self.package_folder}",
                 cwd=src)

    def package_info(self):
        # This is a command-line tool package - declare bindirs
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
