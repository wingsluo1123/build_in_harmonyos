#!/usr/bin/env python3
"""Conan recipe for libblockdev 3.4.0 — Autotools (configure + make).

Library for manipulating block devices with plugin-based architecture.
Only the loop plugin is enabled; all other plugins are disabled because
they depend on Linux kernel subsystems not available on HarmonyOS.

Key adaptation points:
  - R26: libblockdev is NOT a system-name library → default shared
  - R32: settings.os check uses in ("Linux", "OHOS")
  - R33: compiler from Conan conf, not shell env vars
  - libkmod stub: built as part of this package (no kmod on OHOS)
  - libudev: provided by libudev-zero conan dependency
  - Patches: config.guess (HarmonyOS triplet), umask fix, libtool/automake downgrade
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibblockdevConan(ConanFile):
    name = "libblockdev"
    version = "3.4.0"
    description = "Library for manipulating block devices with plugin-based architecture"
    license = "LGPL-2.0"
    homepage = "https://github.com/storaged-project/libblockdev"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)
        # Also export libkmod stub sources
        copy(self, "libkmod-stub/*", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        self.requires("glib/2.84.0.1")
        self.requires("libudev-zero/1.0.4")
        self.requires("uuid/2.40.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: Check platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"{self.name} only supports Linux/OHOS")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R33: Get compiler from Conan conf, not shell env vars
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")

        # Plugin configuration - only loop plugin enabled
        # Other plugins depend on Linux kernel subsystems not available on OHOS
        tc.configure_args.append("--without-btrfs")
        tc.configure_args.append("--without-lvm")
        tc.configure_args.append("--without-lvm-dbus")
        tc.configure_args.append("--without-mpath")
        tc.configure_args.append("--without-dm")
        tc.configure_args.append("--without-crypto")
        tc.configure_args.append("--without-escrow")
        tc.configure_args.append("--without-nvdimm")
        tc.configure_args.append("--without-nvme")
        tc.configure_args.append("--without-smart")
        tc.configure_args.append("--without-smartmontools")
        tc.configure_args.append("--without-s390")
        tc.configure_args.append("--without-fs")
        tc.configure_args.append("--without-part")
        tc.configure_args.append("--without-swap")
        tc.configure_args.append("--without-tools")
        tc.configure_args.append("--without-python3")
        tc.configure_args.append("--without-mdraid")
        tc.configure_args.append("--with-loop")
        # Set SHELL to HarmonyOS bash path (avoid /bin/bash not found)
        tc.configure_args.append("SHELL=/data/service/hnp/bin/bash")
        # OHOS: ELF signing required to run binaries, so configure's AC_TRY_RUN
        # tests fail with SIGTRAP. Set --host to skip run tests (cross-compile mode).
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # glib's .pc doesn't include -lintl, but glib references g_libintl_* symbols
        # Also add pcre2, ffi, zlib since glib's conan .pc may not include all transitive deps
        tc.extra_ldflags.extend(["-lintl", "-lpcre2-8", "-lffi", "-lz"])
        tc.generate()

        # Generate PkgConfig files for conan dependencies
        pkg_config = PkgConfigDeps(self)
        pkg_config.generate()

        # Create libudev.pc wrapper — libblockdev's configure looks for "libudev"
        # via pkg-config, but libudev-zero generates libudev-zero.pc
        libudev_pc = os.path.join(self.generators_folder, "libudev.pc")
        with open(libudev_pc, "w") as f:
            f.write("Name: libudev\n")
            f.write("Description: libudev (provided by libudev-zero)\n")
            f.write("Version: 251\n")
            f.write("Requires: libudev-zero\n")

    def build(self):
        apply_conandata_patches(self)

        # Build libkmod stub library (no kmod on HarmonyOS)
        # R33: Get compiler from Conan conf
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_executables.get("c", "clang")
        ar = "llvm-ar"
        if not shutil.which(ar):
            ar = "ar"

        stub_src = os.path.join(self.export_sources_folder, "libkmod-stub")
        if os.path.isdir(stub_src):
            # Copy stub sources to build directory
            build_stub = os.path.join(self.source_folder, "libkmod-stub")
            if not os.path.exists(build_stub):
                os.makedirs(build_stub)
            copy(self, "*.c", stub_src, build_stub)
            copy(self, "*.h", stub_src, build_stub)

            # Compile stub library
            self.run(f"{cc} -fPIC -O2 -c {build_stub}/libkmod.c -o {build_stub}/libkmod.o -I{build_stub}")
            self.run(f"{ar} rcs {build_stub}/libkmod.a {build_stub}/libkmod.o")

            # Install stub to a prefix that configure can find
            stub_prefix = os.path.join(self.build_folder, "kmod-stub-install")
            os.makedirs(os.path.join(stub_prefix, "lib"), exist_ok=True)
            os.makedirs(os.path.join(stub_prefix, "include"), exist_ok=True)
            os.makedirs(os.path.join(stub_prefix, "lib", "pkgconfig"), exist_ok=True)
            copy(self, "libkmod.a", build_stub, os.path.join(stub_prefix, "lib"))
            copy(self, "libkmod.h", build_stub, os.path.join(stub_prefix, "include"))

            # Create libkmod.pc
            kmod_pc = os.path.join(stub_prefix, "lib", "pkgconfig", "libkmod.pc")
            with open(kmod_pc, "w") as f:
                f.write(f"prefix={stub_prefix}\n")
                f.write("exec_prefix=${prefix}\n")
                f.write("libdir=${exec_prefix}/lib\n")
                f.write("includedir=${prefix}/include\n\n")
                f.write("Name: libkmod\n")
                f.write("Description: libkmod (stub for HarmonyOS)\n")
                f.write("Version: 33\n")
                f.write("Libs: -L${libdir} -lkmod\n")
                f.write("Cflags: -I${includedir}\n")

            # Add stub prefix to PKG_CONFIG_PATH via environment
            pkg_config_path = os.environ.get("PKG_CONFIG_PATH", "")
            os.environ["PKG_CONFIG_PATH"] = f"{stub_prefix}/lib/pkgconfig:{pkg_config_path}"

        # Touch generated files to prevent automake regeneration
        # (patches modify m4 files, which triggers aclocal rebuild)
        m4_dir = os.path.join(self.source_folder, "m4")
        if os.path.isdir(m4_dir):
            for f in os.listdir(m4_dir):
                os.utime(os.path.join(m4_dir, f), None)
        aclocal_m4 = os.path.join(self.source_folder, "aclocal.m4")
        if os.path.exists(aclocal_m4):
            os.utime(aclocal_m4, None)
        configure = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure):
            os.utime(configure, None)
        for root, dirs, files in os.walk(self.source_folder):
            for fname in files:
                if fname == "Makefile.in" or fname == "Makefile":
                    os.utime(os.path.join(root, fname), None)

        autotools = Autotools(self)
        autotools.configure()
        # Fix SHELL path in all generated Makefiles (/bin/bash → HarmonyOS bash path)
        bash_path = shutil.which("bash") or "/data/service/hnp/bin/bash"
        for root, dirs, files in os.walk(self.source_folder):
            for fname in files:
                if fname == "Makefile":
                    fpath = os.path.join(root, fname)
                    with open(fpath, "r") as f:
                        content = f.read()
                    if content.count("/bin/bash") > 0:
                        # Replace exact SHELL = /bin/bash, not substrings of longer paths
                        content = content.replace("SHELL = /bin/bash\n", f"SHELL = {bash_path}\n")
                        content = content.replace("SHELL=/bin/bash\n", f"SHELL={bash_path}\n")
                        with open(fpath, "w") as f:
                            f.write(content)
        autotools.make(args=["-j1", f"SHELL={bash_path}"])

    def package(self):
        autotools = Autotools(self)
        # Fix SHELL in Makefiles again (package runs in a new context)
        bash_path = shutil.which("bash") or "/data/service/hnp/bin/bash"
        for root, dirs, files in os.walk(self.source_folder):
            for fname in files:
                if fname == "Makefile":
                    fpath = os.path.join(root, fname)
                    with open(fpath, "r") as f:
                        content = f.read()
                    if content.count("/bin/bash") > 0:
                        content = content.replace("SHELL = /bin/bash\n", f"SHELL = {bash_path}\n")
                        content = content.replace("SHELL=/bin/bash\n", f"SHELL={bash_path}\n")
                        with open(fpath, "w") as f:
                            f.write(content)
        # Use -j1 to avoid HMDFS FIFO issues
        autotools.install(args=["-j1", f"SHELL={bash_path}"])

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "blockdev")
        self.cpp_info.libs = ["blockdev", "bd_utils", "bd_loop"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # Transitive dependencies for consumers
        self.cpp_info.requires = ["glib::glib-2.0", "libudev-zero::libudev-zero", "uuid::uuid"]
        # System libs: libblockdev uses dlopen for plugin loading
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread", "m"]
