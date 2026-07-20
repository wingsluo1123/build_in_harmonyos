#!/usr/bin/env python3
"""Conan recipe for GNU Guile 2.2.7 for OpenHarmony.

Build system: Autotools (configure + make)

Key design:
- package_type = "library" (primarily used as an embeddable Scheme library)
- Also provides bindirs = ["bin"] for the guile executable
- Conan dep: gc/8.2.12@ohpcd/stable (Boehm-Demers-Weiser GC)
- Non-conan system deps (gmp, libffi, libunistring, libltdl) found via
  ~/usr/local search paths — these are pre-installed on the build machine
- Signal 5 (SIGTRAP) during .go compilation is tolerated via make -k
- .go files are copied from the source tarball's prebuilt/ directory
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class GuileConan(ConanFile):
    name = "guile"
    version = "2.2.7"
    description = (
        "GNU's Ubiquitous Intelligent Language for Extension (Guile) — "
        "Scheme interpreter and embeddable library"
    )
    license = "LGPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/guile/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gc (Boehm GC) is the only conan-managed dependency.
        # gmp, libffi, libunistring, libltdl are pre-installed at
        # ~/usr/local/ on the build machine (see generate()).
        self.requires("gc/8.2.12")

    def build_requirements(self):
        self.tool_requires("pkgconf/2.5.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # System-local prefix for non-conan deps (gmp, libffi, etc.)
        local_prefix = os.path.expanduser("~/usr/local")

        tc = AutotoolsToolchain(self)
        tc.extra_cflags.append(f"-I{local_prefix}/include")
        tc.extra_ldflags.append(
            f"-L{local_prefix}/lib -Wl,-rpath,{local_prefix}/lib"
        )
        tc.generate()

        deps = AutotoolsDeps(self)
        deps.generate()

        pkg = PkgConfigDeps(self)
        pkg.generate()

        # Add ~/usr/local to PKG_CONFIG_PATH for non-conan deps
        env = Environment()
        env.append("PKG_CONFIG_PATH", f"{local_prefix}/lib/pkgconfig")
        env.vars(self).save_script("conanenv_non_conan_deps")

    def build(self):
        """Build guile from source.

        Signal 5 (SIGTRAP) occurs during .go (Scheme bytecode) compilation
        on HarmonyOS due to GC/HarmonyOS limitations. ``make -k`` tolerates
        these errors and continues building .so libraries and binaries, which
        are compiled before the .go targets.

        The .go files are NOT rebuilt — they are copied from the source
        tarball's ``prebuilt/`` directory in ``package()``.
        """
        apply_conandata_patches(self)
        autotools = Autotools(self)

        # The CI profile may set CONFIG_SHELL and CC to paths that don't
        # exist on the development machine (e.g. /data/service/hnp/bin/...).
        # We override these for the configure command with available tools.
        local_prefix = os.path.expanduser("~/usr/local")
        bash = os.path.join(local_prefix, "bin", "bash")
        if not os.path.isfile(bash):
            bash = shutil.which("bash") or "/bin/sh"
        cc = os.path.join(local_prefix, "bin", "clang")
        if not os.path.isfile(cc):
            cc = shutil.which("clang") or "clang"
        cxx = os.path.join(local_prefix, "bin", "clang++")
        if not os.path.isfile(cxx):
            cxx = shutil.which("clang++") or "clang++"

        # Find the configure script (it may be in build_folder or its parent)
        configure_path = os.path.join(self.build_folder, "configure")
        if not os.path.isfile(configure_path):
            configure_path = os.path.join(
                os.path.dirname(self.build_folder), "configure"
            )

        # Run configure with correct shell and compiler overrides.
        # Use distinct --build and --host triplets to force cross-compile
        # mode so configure does not try to run the test binary (libcord.so
        # from the system path causes a runtime load failure).
        self.run(
            f'CONFIG_SHELL="{bash}" SHELL="{bash}" '
            f'CC="{cc}" CXX="{cxx}" '
            f'LD_LIBRARY_PATH="{local_prefix}/lib'
            f'${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}" '
            f'PKG_CONFIG_PATH="{local_prefix}/lib/pkgconfig'
            f'${{PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}}" '
            f'"{bash}" "{configure_path}" '
            f'--build=aarch64-unknown-linux-gnu '
            f'--host=aarch64-unknown-linux-ohos '
            f'--enable-shared --disable-static '
            f'--prefix=/ '
            f"--bindir=${{prefix}}/bin "
            f"--sbindir=${{prefix}}/bin "
            f"--libdir=${{prefix}}/lib "
            f"--includedir=${{prefix}}/include "
            f"--oldincludedir=${{prefix}}/include",
            env="conanbuild",
        )

        # Signal 5 (SIGTRAP) during .go compilation is tolerated via make -k.
        # .so libraries are built before .go files, so they should succeed.
        autotools.make(args=["-k"])

    def package(self):
        """Package guile from build output and source tarball.

        - .so files, binaries, and pkg-config come from the build output
        - .go files come from the source tarball's prebuilt/ directory
        - .scm files come from the source module/ directory
        - .h headers come from the source libguile/ directory
        """
        pkg = self.package_folder
        build_folder = self.build_folder
        source_folder = self.source_folder

        # ── Library files (.so) from build output ────────────────────
        lib_src = os.path.join(build_folder, "libguile", ".libs")
        if os.path.isdir(lib_src):
            copy(self, "libguile-2.2.so*", src=lib_src,
                 dst=os.path.join(pkg, "lib"))
            copy(self, "libguile-2.2.a", src=lib_src,
                 dst=os.path.join(pkg, "lib"))

        # ── Binaries from build output ────────────────────────────────
        if os.path.isdir(lib_src):
            copy(self, "guile", src=lib_src,
                 dst=os.path.join(pkg, "bin"))

        # guile-config and guild are scripts in meta/
        meta_dir = os.path.join(build_folder, "meta")
        if os.path.isdir(meta_dir):
            copy(self, "guile-config", src=meta_dir,
                 dst=os.path.join(pkg, "bin"))
            copy(self, "guild", src=meta_dir,
                 dst=os.path.join(pkg, "bin"))

        # ── Headers from source libguile/ ────────────────────────────
        header_src = os.path.join(source_folder, "libguile")
        if os.path.isdir(header_src):
            copy(self, "*.h", src=header_src,
                 dst=os.path.join(pkg, "include/guile/2.2/libguile"))

        # ── .go files from source tarball prebuilt/ ──────────────────
        go_src = os.path.join(source_folder, "prebuilt",
                              "64-bit-little-endian")
        if os.path.isdir(go_src):
            for root, dirs, files in os.walk(go_src):
                rel = os.path.relpath(root, go_src)
                dst = os.path.join(pkg, "lib/guile/2.2/ccache", rel)
                os.makedirs(dst, exist_ok=True)
                for f in files:
                    if f.endswith(".go"):
                        shutil.copy2(os.path.join(root, f),
                                     os.path.join(dst, f))

        # ── .scm files from source module/ ────────────────────────────
        scm_src = os.path.join(source_folder, "module")
        if os.path.isdir(scm_src):
            for root, dirs, files in os.walk(scm_src):
                # Skip hidden directories (.deps, .libs, etc.)
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                rel = os.path.relpath(root, scm_src)
                dst = os.path.join(pkg, "share/guile/2.2", rel)
                os.makedirs(dst, exist_ok=True)
                for f in files:
                    if f.endswith(".scm"):
                        shutil.copy2(os.path.join(root, f),
                                     os.path.join(dst, f))

        # ── pkg-config file from build output ────────────────────────
        pc_src = os.path.join(build_folder, "meta", "guile-2.2.pc")
        if os.path.exists(pc_src):
            os.makedirs(os.path.join(pkg, "lib/pkgconfig"),
                        exist_ok=True)
            pc_dst = os.path.join(pkg, "lib/pkgconfig/guile-2.2.pc")
            shutil.copy2(pc_src, pc_dst)
            # Fix absolute build paths to use pkg-config variables
            local_prefix = os.path.expanduser("~/usr/local")
            replace_in_file(self, pc_dst,
                            local_prefix, "${prefix}")
            # Remove explicit -lgc, -lgmp, -lffi (handled by conan deps)
            replace_in_file(self, pc_dst, "-lgc", "")
            replace_in_file(self, pc_dst, "-lgmp", "")
            replace_in_file(self, pc_dst, "-lffi", "")

        # ── License ──────────────────────────────────────────────────
        copy(self, "COPYING*", src=source_folder,
             dst=os.path.join(pkg, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["guile-2.2"]
        self.cpp_info.set_property("pkg_config_name", "guile-2.2")
        # Headers are in include/guile/2.2/libguile/
        self.cpp_info.includedirs = ["include/guile/2.2"]
        # Also provide bindirs for the guile executable
        self.cpp_info.bindirs = ["bin"]
        # Scheme runtime files
        self.cpp_info.resdirs = ["share/guile"]
        # R32: System libs for Linux and OHOS
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
