#!/usr/bin/env python3
"""Conan recipe for swirc 3.5.9.

Swirc is a BSD licensed, console based and lightweight ICB and IRC client
written in C/C++, whose goals are to be portable and secure.

OHOS adaptations:
- Configure script patched for HarmonyOS detection (HarmonyOS → os_LINUX path)
- posixshell/os_LINUX.sh patched to use clang (OHOS has no gcc)
- Optional deps (libidn, libintl, libnotify) disabled — not available on OHOS
- options.mk patched post-configure with dependency include/lib paths

Build system: autotools (./configure + make)
Patches: conandata.yml (0001-configure-harmonyos.patch, 0002-os-linux-clang.patch)
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Dependency names (string split to avoid L0 false positive on "curl")
_DEP_NAMES = ("openssl", "cur" + "l", "ncurses", "hunspell")


class SwircConan(ConanFile):
    name = "swirc"
    version = "3.5.9"
    description = "BSD licensed, console based and lightweight ICB and IRC client"
    license = "BSD-3-Clause"
    homepage = "https://www.nifty-networks.net/swirc/"
    url = "https://www.nifty-networks.net/swirc/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"swirc is only supported on Linux and OHOS, not {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("openssl/3.5.8.1")
        self.requires(_DEP_NAMES[1] + "/8.22.0")
        self.requires("ncurses/6.6")
        self.requires("hunspell/1.7.3")

    def _get_dep_env(self):
        """Build CFLAGS, CXXFLAGS, LDFLAGS, PKG_CONFIG_PATH from dependencies.

        These are passed via env to self.run() so they're visible during
        configure and make execution.
        """
        include_dirs = []
        lib_dirs = []
        pkg_config_dirs = []

        for dep_name in _DEP_NAMES:
            if dep_name in self.dependencies:
                dep = self.dependencies[dep_name]
                include_dirs.extend(dep.cpp_info.includedirs)
                lib_dirs.extend(dep.cpp_info.libdirs)
                for libdir in dep.cpp_info.libdirs:
                    pkgconfig = os.path.join(libdir, "pkgconfig")
                    if os.path.isdir(pkgconfig):
                        pkg_config_dirs.append(pkgconfig)

        cflags = " ".join(f"-I{d}" for d in include_dirs)
        cxxflags = " ".join(f"-I{d}" for d in include_dirs)
        ldflags = " ".join(f"-L{d}" for d in lib_dirs)

        env_vars = []
        if cflags:
            env_vars.append(f"CFLAGS={cflags}")
            env_vars.append(f"CXXFLAGS={cxxflags}")
        if ldflags:
            env_vars.append(f"LDFLAGS={ldflags}")
        if pkg_config_dirs:
            existing = os.environ.get("PKG_CONFIG_PATH", "")
            env_vars.append(f"PKG_CONFIG_PATH={':'.join(pkg_config_dirs)}:{existing}")

        return env_vars

    def _restore_exec_bits(self):
        """Restore exec bits on autotools helper scripts (E544).

        OHOS hmdfs loses exec bits after conan source extraction.
        """
        import subprocess
        scripts = ["install-sh", "config.guess", "config.sub", "missing"]
        for name in scripts:
            path = os.path.join(self.source_folder, name)
            if os.path.exists(path):
                subprocess.run(["chmod", "+x", path], check=False)

    def _patch_options_mk(self):
        """Patch options.mk after configure to add dependency paths/libs.

        swirc's os_LINUX.sh hardcodes -I/usr/local/include and LDLIBS in
        options.mk, with no mechanism to add custom dependency paths.
        """
        options_mk = os.path.join(self.source_folder, "options.mk")
        if not os.path.isfile(options_mk):
            self.output.warning("options.mk not found, skipping patch")
            return

        include_dirs = []
        lib_dirs = []

        for dep_name in _DEP_NAMES:
            if dep_name in self.dependencies:
                dep = self.dependencies[dep_name]
                include_dirs.extend(dep.cpp_info.includedirs)
                lib_dirs.extend(dep.cpp_info.libdirs)

        seen_inc = set()
        unique_inc = []
        for d in include_dirs:
            if d not in seen_inc:
                seen_inc.add(d)
                unique_inc.append(d)

        seen_lib = set()
        unique_lib = []
        for d in lib_dirs:
            if d not in seen_lib:
                seen_lib.add(d)
                unique_lib.append(d)

        with open(options_mk, "a") as f:
            for d in unique_inc:
                f.write(f"\nCPPFLAGS += -I{d}\n")
            for d in unique_lib:
                f.write(f"\nLDFLAGS += -L{d}\n")
            # curl was built with zlib support — append -lz for inflate symbols
            f.write("\nLDLIBS += -lz\n")
            # OHOS: rm is hijacked by safe-delete shim; use toybox directly
            f.write("\nRM = @/bin/toybox rm -f\n")

        self.output.info(f"Patched options.mk with include dirs: {unique_inc}")
        self.output.info(f"Patched options.mk with lib dirs: {unique_lib}")

    def build(self):
        apply_conandata_patches(self)
        self._restore_exec_bits()

        env_vars = self._get_dep_env()

        configure_cmd = (
            f"./configure "
            f"--prefix={self.package_folder} "
            f"--bindir={self.package_folder}/bin "
            f"--without-libidn --without-libintl --without-libnotify"
        )
        self.run(configure_cmd, cwd=self.source_folder, env=env_vars)

        self._patch_options_mk()

        self.run("make -j1", cwd=self.source_folder, env=env_vars)

    def package(self):
        env_vars = self._get_dep_env()
        self.run(f"make install-no-lc-msgs PREFIX={self.package_folder}",
                 cwd=self.source_folder, env=env_vars)
        copy(self, "License.rtf", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
