#!/usr/bin/env python3
"""Conan recipe — perl-params-classify 0.015 (Perl XS/C module)

This is a Perl XS module that uses `perl Build.PL` (Module::Build, not autotools).
It compiles C code (Classify.xs) into a shared library (Classify.so) for Perl.

Note: This is a Perl XS module, not a terminal tool. R26 (static linking)
is not applicable for shared library Perl modules. The .so is loaded by Perl
at runtime via DynaLoader.

OHOS platform fix: Build.PL is patched to override cbuilder() and have_c_compiler()
to fix linker flags (remove -fstack-protector-strong, add -L paths for musl/system libs).
"""

import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class PerlparamsclassifyConan(ConanFile):
    name = "perl-params-classify"
    version = "0.015"
    description = "argument type classification (Perl XS module)"
    license = "MIT"
    homepage = "https://metacpan.org/dist/Params-Classify"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # musl C library headers and system libraries paths
    _musl_inc = os.path.expanduser("~/usr/local/include")
    _musl_lib = os.path.expanduser("~/usr/local/lib")

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"perl-params-classify does not support os={self.settings.os}"
            )

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = Environment()
        env.define("CC", "clang")
        env.define("CFLAGS", "-fPIC -O2")
        # Set CPATH for musl headers (sys/types.h, stdio.h, etc.)
        env.append_path("CPATH", self._musl_inc)
        # Set LIBRARY_PATH for system libs
        env.append_path("LIBRARY_PATH", self._musl_lib)
        env.append_path("LIBRARY_PATH", "/system/lib64")
        envvars = env.vars(self)
        envvars.save_script("perl_params_classify_env")

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        # Use Module::Build (Build.PL) instead of Makefile.PL
        self.run(
            f"cd {src} && perl Build.PL --install_base={self.package_folder} "
            f"&& ./Build",
            env=["perl_params_classify_env"]
        )

    def package(self):
        src = self.source_folder
        # Install using ./Build install
        self.run(
            f"cd {src} && ./Build install --install_base={self.package_folder}",
            env=["perl_params_classify_env"]
        )
        # Copy .so to standard lib/ directory for artifact discovery (G4)
        so_files = glob.glob(os.path.join(src, "blib", "arch", "auto", "Params", "Classify", "*.so"))
        if so_files:
            copy(self, "*.so", os.path.join(src, "blib", "arch", "auto", "Params", "Classify"),
                 os.path.join(self.package_folder, "lib"))
        # Copy .pm module file for completeness
        pm_files = glob.glob(os.path.join(src, "blib", "lib", "Params", "*.pm"))
        if pm_files:
            copy(self, "*.pm", os.path.join(src, "blib", "lib", "Params"),
                 os.path.join(self.package_folder, "lib", "Params"))

    def package_info(self):
        self.cpp_info.libs = ["Classify"]
        self.cpp_info.libdirs = ["lib"]
