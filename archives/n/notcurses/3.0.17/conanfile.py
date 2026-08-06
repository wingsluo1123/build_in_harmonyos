#!/usr/bin/env python3
"""Conan recipe — notcurses 3.0.17 (CMake).

TUI library for modern terminal applications with multimedia support.
Depends on ncurses (system-installed via cmd-pkgs), libunistring, libdeflate.

R26: Static linking for system same-name libraries (ncurses).
R32: settings.os must check in ("Linux", "OHOS").
R33: Compilers from Conan toolchain, not shell env vars.

All source modifications are applied via patches declared in conandata.yml:
  0001-CMakeLists.txt.patch  - Make libm/librt optional (not always present on OHOS)
  0002-src-demo-input.c.patch - Replace pthread_cancel with pthread_detach
  0003-src-demo-reel.c.patch  - Replace pthread_cancel with pthread_detach
  0004-src-lib-fbuf.h.patch   - Fix readlink buffer handling for OHOS
  0005-src-lib-fd.c.patch     - Replace pthread_cancel with pthread_detach
  0006-src-lib-in.c.patch     - Skip DA1/DA2 queries, replace ppoll with poll
  0007-src-lib-internal.h.patch - Replace cancel_and_join with pthread_detach
  0008-src-lib-termdesc.c.patch - Skip terminal queries that block on OHOS
  0009-src-lib-reader.c.patch - Handle Enter key, fix cursor on clear
  0010-src-lib-in.h.patch     - Declare stop_inputlayer for OHOS
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, apply_conandata_patches,
    export_conandata_patches, copy,
)
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


def _get_prefix():
    """Get the prefix for installing/finding system dependencies."""
    prefix = os.environ.get("DEFAULT_PREFIX")
    if prefix:
        return prefix
    return os.path.join(os.path.expanduser("~"), "usr", "local")


def _is_ncurses_installed(prefix):
    """Check if ncurses library is installed at prefix."""
    return os.path.exists(os.path.join(prefix, "lib", "libncursesw.a"))


def _is_ncurses_headers_installed(prefix):
    """Check if ncurses headers are installed at prefix."""
    return os.path.exists(os.path.join(prefix, "include", "curses.h"))


def _install_cmd_pkg(name, version, prefix):
    """Download and install a cmd-pkgs prebuilt package."""
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh"
    cmd = f'curl -fsSL {url} | sh -s -- {name} {version} {prefix}'
    subprocess.run(cmd, shell=True, timeout=300, capture_output=True, text=True)


def _install_ncurses_headers(prefix, header_tarball):
    """Install ncurses headers from bundled tarball (cmd-pkgs only ships libs)."""
    import tarfile
    inc_dst = os.path.join(prefix, "include")
    os.makedirs(inc_dst, exist_ok=True)
    if header_tarball and os.path.exists(header_tarball):
        with tarfile.open(header_tarball, "r:gz") as tar:
            tar.extractall(inc_dst)


def _ensure_ncurses_pkgconfig(prefix):
    """Create pkg-config file for ncursesw if not present."""
    pkgconfig_dir = os.path.join(prefix, "lib", "pkgconfig")
    os.makedirs(pkgconfig_dir, exist_ok=True)
    pc_path = os.path.join(pkgconfig_dir, "ncursesw.pc")
    if not os.path.exists(pc_path):
        with open(pc_path, "w") as f:
            f.write(
                f"prefix={prefix}\n"
                f"exec_prefix=${{prefix}}\n"
                f"libdir=${{exec_prefix}}/lib\n"
                f"includedir=${{prefix}}/include\n"
                f"\n"
                f"Name: ncursesw\n"
                f"Description: ncurses 6.4 library (widechar)\n"
                f"Version: 6.4\n"
                f"Libs: -L${{libdir}} -lncursesw\n"
                f"Cflags: -I${{includedir}}\n"
            )


class NotcursesConan(ConanFile):
    name = "notcurses"
    version = "3.0.17"
    description = "TUI library for modern terminal applications with multimedia support"
    license = "Apache-2.0"
    homepage = "https://github.com/dankamongmen/notcurses"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "ncurses-headers.tar.gz", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        # ncurses is a system-installed dependency (via cmd-pkgs), not a Conan package.
        self.requires("libunistring/1.0")
        self.requires("libdeflate/1.25")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "notcurses is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        prefix = _get_prefix()
        hdr_tarball = os.path.join(self.source_folder, "ncurses-headers.tar.gz")

        # Ensure system ncurses is installed via cmd-pkgs
        if not _is_ncurses_installed(prefix):
            _install_cmd_pkg("ncurses", "6.4", prefix)
        # cmd-pkgs ncurses only ships library, not headers - install from bundled tarball
        if not _is_ncurses_headers_installed(prefix):
            _install_ncurses_headers(prefix, hdr_tarball)
        # Create pkg-config file for ncursesw
        _ensure_ncurses_pkgconfig(prefix)

        tc = CMakeToolchain(self)
        # R26: System-name libraries default to static
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Build options
        tc.variables["USE_MULTIMEDIA"] = "none"
        tc.variables["USE_DOCTEST"] = "OFF"
        tc.variables["USE_PANDOC"] = "OFF"
        # System ncurses: add include/lib paths via flags (not CMAKE_FIND_ROOT_PATH
        # which would restrict Conan dependency searches and break check_include_file)
        ncurses_inc = os.path.join(prefix, "include")
        ncurses_lib = os.path.join(prefix, "lib")
        if os.path.isdir(ncurses_inc):
            tc.extra_cflags.append("-I" + ncurses_inc)
        if os.path.isdir(ncurses_lib):
            tc.variables["CMAKE_LIBRARY_PATH"] = ncurses_lib
        # Explicitly add Conan dependency include dirs for check_include_file
        # (CMakeToolchain should do this, but some packages' headers aren't found)
        for dep_name in self.deps_cpp_info:
            dep = self.deps_cpp_info[dep_name]
            for inc_dir in dep.include_dirs:
                tc.extra_cflags.append("-I" + inc_dir)
        # Set PKG_CONFIG_PATH for ncursesw discovery
        pkgconfig_path = os.path.join(prefix, "lib", "pkgconfig")
        if os.path.isdir(pkgconfig_path):
            env_prefix = os.environ.get("PKG_CONFIG_PATH", "")
            os.environ["PKG_CONFIG_PATH"] = (
                pkgconfig_path + (":" + env_prefix if env_prefix else "")
            )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["notcurses", "notcurses-core"]
        # System dependency: ncurses (static, via cmd-pkgs)
        prefix = _get_prefix()
        self.cpp_info.system_libs = ["m"]
        # Add ncurses lib path and flags
        ncurses_lib = os.path.join(prefix, "lib")
        if os.path.isdir(ncurses_lib):
            self.cpp_info.libdirs.append(ncurses_lib)
            self.cpp_info.libs.append("ncursesw")
        ncurses_inc = os.path.join(prefix, "include")
        if os.path.isdir(ncurses_inc):
            self.cpp_info.includedirs.append(ncurses_inc)
