#!/usr/bin/env python3
"""Conan recipe — i686-elf-grub 2.12 (GRUB bootloader cross-compile for i686-elf target).

Cross-compiled GRUB 2.12 running on aarch64-ohos, generating i686 platform GRUB images.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import Environment

import os
import shutil


class I686ElfGrubConan(ConanFile):
    name = "i686-elf-grub"
    version = "2.12"
    description = "GNU GRUB bootloader cross-compiled for i686-elf target"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/grub/"
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
        tc_env = Environment()
        _bash = shutil.which("bash") or "bash"
        _cc = shutil.which("clang") or "clang"
        _cxx = shutil.which("clang++") or "clang++"
        tc_env.define("CONFIG_SHELL", _bash)
        tc_env.define("SHELL", _bash)
        tc_env.define("CC", _cc)
        tc_env.define("CXX", _cxx)
        tc_env.define("AR", "llvm-ar")
        tc_env.define("RANLIB", "llvm-ranlib")
        tc_env.define("NM", "llvm-nm")
        tc_env.define("STRIP", "llvm-strip")
        tc_env.define("CPPFLAGS", "")
        envvars = tc_env.vars(self, scope="build")
        envvars.save_script("env_override")

    def build(self):
        apply_conandata_patches(self)

        _bash = shutil.which("bash") or "bash"
        _cc = shutil.which("clang") or "clang"
        _cxx = shutil.which("clang++") or "clang++"

        src = self.source_folder or "."

        # R32: Support both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"OS {self.settings.os} not supported")

        # Create i686-elf cross-compiler wrapper scripts (CI env has no i686-elf-gcc)
        cross_bindir = self._setup_cross_tools(src)

        env_prefix = (
            f"CONFIG_SHELL={_bash} SHELL={_bash} "
            f"PATH={cross_bindir}:$PATH "
            f"CC={_cc} CXX={_cxx} "
            f"AR=llvm-ar RANLIB=llvm-ranlib NM=llvm-nm STRIP=llvm-strip "
            f"CPPFLAGS='' "
            f"CFLAGS='-O2' CXXFLAGS='-O2' "
        )

        # Fix umask 077→022 in configure script (HMDFS permission issue)
        self._fix_configure_umask()

        # Configure: cross-compile for i686-elf target
        # Set umask 022 to fix HMDFS permission issues (umask 077 in config.status)
        self.run(f"umask 022; {env_prefix} {src}/configure --target=i686-elf "
                 f"--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu "
                 f"--prefix=/ --disable-werror --disable-nls",
                 cwd=src)

        # Fix config.status umask 077→022 (HMDFS permission issue)
        # configure creates config.status with umask 077 internally
        self._fix_umask()

        # Re-run config.status with fixed umask to regenerate Makefiles
        self.run(f"umask 022; {env_prefix} ./config.status", cwd=src)

        # Fix major.h: include sys/sysmacros.h unconditionally (OHOS has it but configure can't detect)
        self._fix_major_h()

        # Fix genmoddep.awk: allow _GLOBAL_OFFSET_TABLE_ and __x86.get_pc_thunk.* symbols
        self._fix_genmoddep_awk()

        # Create empty extra_deps.lst (missing from release tarball)
        with open(os.path.join(src, "grub-core", "extra_deps.lst"), "w"):
            pass

        # Build with -j1 (HMDFS doesn't support mkfifo)
        self.run(f"umask 022; {env_prefix} make -j1", cwd=src)

    def _setup_cross_tools(self, src):
        """Create i686-elf cross-compiler wrapper scripts using clang --target=i686-elf.

        GRUB's configure looks for i686-elf-gcc in PATH. The CI environment only has
        host clang (aarch64), so we create wrapper scripts that add --target=i686-elf.
        """
        import stat
        bindir = os.path.join(src, ".cross-tools")
        os.makedirs(bindir, exist_ok=True)
        _clang = shutil.which("clang") or "clang"
        _clangxx = shutil.which("clang++") or "clang++"

        # Compiler wrappers: add --target=i686-elf to host clang
        for name, real in [("i686-elf-gcc", _clang), ("i686-elf-cc", _clang),
                           ("i686-elf-c++", _clangxx), ("i686-elf-cpp", _clang)]:
            wrapper = os.path.join(bindir, name)
            with open(wrapper, "w") as f:
                f.write(f"#!/bin/sh\nexec {real} --target=i686-elf \"$@\"\n")
            os.chmod(wrapper, os.stat(wrapper).st_mode | stat.S_IEXEC)

        # LLVM binutils wrappers (LLVM tools are target-agnostic, no --target needed)
        for name, real in [("i686-elf-ar", "llvm-ar"), ("i686-elf-ranlib", "llvm-ranlib"),
                           ("i686-elf-nm", "llvm-nm"), ("i686-elf-strip", "llvm-strip"),
                           ("i686-elf-objcopy", "llvm-objcopy"), ("i686-elf-as", "llvm-as"),
                           ("i686-elf-ld", "ld.lld")]:
            real_path = shutil.which(real) or real
            wrapper = os.path.join(bindir, name)
            with open(wrapper, "w") as f:
                f.write(f"#!/bin/sh\nexec {real_path} \"$@\"\n")
            os.chmod(wrapper, os.stat(wrapper).st_mode | stat.S_IEXEC)

        return bindir

    def _fix_umask(self):
        """Fix umask 077→022 in config.status (HMDFS permission issue)."""
        src = self.source_folder or "."
        for config_status in [
            os.path.join(src, "config.status"),
            os.path.join(src, "grub-core", "config.status"),
        ]:
            if os.path.exists(config_status):
                with open(config_status, "r") as f:
                    content = f.read()
                content = content.replace("umask 077", "umask 022")
                with open(config_status, "w") as f:
                    f.write(content)

    def _fix_configure_umask(self):
        """Fix umask 077→022 in configure script (HMDFS permission issue)."""
        src = self.source_folder or "."
        configure = os.path.join(src, "configure")
        if os.path.exists(configure):
            with open(configure, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure, "w") as f:
                f.write(content)

    def _fix_major_h(self):
        """Fix include/grub/osdep/major.h to include sys/sysmacros.h unconditionally."""
        src = self.source_folder or "."
        major_h = os.path.join(src, "include", "grub", "osdep", "major.h")
        if os.path.exists(major_h):
            with open(major_h, "r") as f:
                content = f.read()
            old = """#ifdef MAJOR_IN_MKDEV
# include <sys/mkdev.h>
#elif defined (MAJOR_IN_SYSMACROS)
# include <sys/sysmacros.h>
#endif"""
            new = """#ifdef MAJOR_IN_MKDEV
# include <sys/mkdev.h>
#elif defined (MAJOR_IN_SYSMACROS)
# include <sys/sysmacros.h>
#else
# include <sys/sysmacros.h>
#endif"""
            content = content.replace(old, new)
            with open(major_h, "w") as f:
                f.write(content)

    def _fix_genmoddep_awk(self):
        """Fix grub-core/genmoddep.awk to allow cross-compile symbols."""
        src = self.source_folder or "."
        awk_file = os.path.join(src, "grub-core", "genmoddep.awk")
        if os.path.exists(awk_file):
            with open(awk_file, "r") as f:
                content = f.read()
            # Allow _GLOBAL_OFFSET_TABLE_ as undefined symbol
            content = content.replace(
                '$3 != "__gnu_local_gp" && $3 != "_gp_disp"',
                '$3 != "__gnu_local_gp" && $3 != "_gp_disp" && $3 != "_GLOBAL_OFFSET_TABLE_"'
            )
            # Allow __x86.get_pc_thunk.* as duplicate symbols
            content = content.replace(
                '$3 !~ /^\\.refptr\\./ && $3 in symtab',
                '$3 !~ /^\\.refptr\\./ && $3 !~ /^__x86.get_pc_thunk\\./ && $3 in symtab'
            )
            with open(awk_file, "w") as f:
                f.write(content)

    def package(self):
        _bash = shutil.which("bash") or "bash"
        _cc = shutil.which("clang") or "clang"
        _cxx = shutil.which("clang++") or "clang++"
        src = self.source_folder or "."
        cross_bindir = os.path.join(src, ".cross-tools")
        env_prefix = (
            f"CONFIG_SHELL={_bash} SHELL={_bash} "
            f"PATH={cross_bindir}:$PATH "
            f"CC={_cc} CXX={_cxx} "
            f"AR=llvm-ar RANLIB=llvm-ranlib NM=llvm-nm STRIP=llvm-strip "
            f"CPPFLAGS='' "
            f"CFLAGS='-O2' CXXFLAGS='-O2' "
        )
        # Install to package folder (DESTDIR), prefix=/
        self.run(f"umask 022; {env_prefix} make install DESTDIR={self.package_folder}",
                 cwd=src)

    def package_info(self):
        # This is a command-line tool package - declare bindirs
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
