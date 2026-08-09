#!/usr/bin/env python3
"""Conan recipe for irssi 1.4.5 (Autotools) — IRC client for HarmonyOS PC."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class IrssiConan(ConanFile):
    name = "irssi"
    version = "1.4.5"
    description = "Modular IRC client for UNIX systems with text-based terminal UI"
    license = "GPL-2.0-or-later"
    homepage = "https://irssi.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0")
        self.requires("openssl/3.5.6")
        self.requires("ncurses/6.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-perl=no")
        # On HarmonyOS, /lib is a symlink to /system/lib, but the linker
        # (ld.lld) doesn't follow it for -l:ld-musl-aarch64.so.1.
        # Add -L/system/lib to LDFLAGS so the musl dynamic linker is found.
        if self.settings.os in ("Linux", "OHOS"):
            tc.extra_ldflags.append("-L/system/lib")
            tc.extra_ldflags.append("-Wl,-rpath,/system/lib")
        # irssi's configure uses AC_CHECK_LIB for ncurses setupterm,
        # which doesn't use pkg-config. Pass the ncurses lib path and
        # library name explicitly so the check succeeds.
        ncurses_cpp = self.dependencies["ncurses"].cpp_info
        for inc_dir in ncurses_cpp.includedirs:
            tc.extra_cflags.append(f"-I{inc_dir}")
        for lib_dir in ncurses_cpp.libdirs:
            tc.extra_ldflags.append(f"-L{lib_dir}")
        for lib in ncurses_cpp.libs:
            tc.extra_ldflags.append(f"-l{lib}")
        tc.generate()

        # Set LD_LIBRARY_PATH so configure's runtime tests can find
        # shared libraries (glib is shared; musl linker is in /system/lib)
        env = Environment()
        if self.settings.os in ("Linux", "OHOS"):
            env.append("LD_LIBRARY_PATH", ["/system/lib"])
        # Add glib shared library path
        glib_cpp = self.dependencies["glib"].cpp_info
        for lib_dir in glib_cpp.libdirs:
            env.append("LD_LIBRARY_PATH", [lib_dir])
        env.vars(self, "conanbuild").save()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_find_mode", "none")
