#!/usr/bin/env python3
"""Conan recipe — libmpc (GNU MPC) 1.4.1.

GNU MPC is a complex floating-point library for the arithmetic
and evaluation of complex numbers with arbitrarily high precision.
It depends on GMP and MPFR, which are used as system libraries
(installed via harmonybrew), not as Conan packages.
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmpcConan(ConanFile):
    name = "libmpc"
    version = "1.4.1"
    description = "GNU MPC: a library for the arithmetic of complex numbers with arbitrarily high precision"
    license = "LGPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/mpc/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    _ci_paths = {
        "/data/service/hnp/bin/bash": "/storage/Users/currentUser/usr/local/bin/bash",
        "/data/service/hnp/bin/clang": "/storage/Users/currentUser/usr/local/bin/clang",
        "/data/service/hnp/bin/clang++": "/storage/Users/currentUser/usr/local/bin/clang++",
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _patch_env_scripts(self):
        gen_dir = Path(self.generators_folder)
        for env_file in gen_dir.glob("conan*.sh"):
            if not env_file.is_file():
                continue
            content = env_file.read_text(encoding="utf-8")
            changed = False
            for ci_path, local_path in self._ci_paths.items():
                if ci_path in content:
                    content = content.replace(ci_path, local_path)
                    changed = True
            if changed:
                env_file.write_text(content, encoding="utf-8")

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        gmp_prefix = "/storage/Users/currentUser/.harmonybrew/Cellar/gmp/6.3.0"
        mpfr_prefix = "/storage/Users/currentUser/.harmonybrew/Cellar/mpfr/4.2.2"
        tc.configure_args.append(f"--with-gmp={gmp_prefix}")
        tc.configure_args.append(f"--with-mpfr={mpfr_prefix}")
        # Use --no-create to skip config.status execution
        # (we patch and run config.status manually in build())
        tc.configure_args.append("--no-create")
        tc.generate()
        self._patch_env_scripts()

    def build(self):
        apply_conandata_patches(self)
        self._patch_env_scripts()

        autotools = Autotools(self)
        # configure with --no-create: generates config.status but doesn't execute it
        autotools.configure()

        # Patch config.status to fix HMDFS umask 077 permission issue.
        # HMDFS creates directories owned by a different uid; umask 077
        # makes them inaccessible, causing "Permission denied".
        config_status = Path(self.build_folder) / "config.status"
        if config_status.exists():
            content = config_status.read_text(encoding="utf-8")
            content = content.replace("umask 077", "umask 022")
            config_status.write_text(content, encoding="utf-8")
            # Run config.status manually
            self.run("./config.status")

        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["mpc"]
        self.cpp_info.system_libs = ["gmp", "mpfr"]
