#!/usr/bin/env python3
"""Conan recipe — libqalculate 5.11.0 (Autotools).

A multi-purpose desktop calculator library.
Provides arbitrary precision arithmetic, symbolic calculation,
unit conversion, and plotting support.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class LibqalculateConan(ConanFile):
    name = "libqalculate"
    version = "5.11.0"
    description = "A multi-purpose desktop calculator library with arbitrary precision"
    license = "GPL-2.0-or-later"
    homepage = "https://qalculate.github.io/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # System dependencies (pre-installed via cmd-pkgs, not Conan)
    # gmp 6.3.0, mpfr 4.2.1, readline 8.2, libxml2 2.15.3

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        import hashlib
        from conan.tools.files import untar

        sources = self.conan_data["sources"]
        url = sources["url"]
        expected_sha256 = sources["sha256"]
        filename = url.split("/")[-1]

        # Download using curl — Python's urllib fails with HTTPS on CI
        tarball = os.path.join(self.source_folder, filename)
        self.run(f'curl -sL "{url}" -o "{tarball}"')

        # Verify SHA256
        h = hashlib.sha256()
        with open(tarball, "rb") as f:
            h.update(f.read())
        if h.hexdigest() != expected_sha256:
            raise Exception(f"SHA256 mismatch: expected {expected_sha256}, got {h.hexdigest()}")

        # Extract with strip_root
        untar(self, tarball, self.source_folder, strip_root=True)

        # Clean up tarball
        os.remove(tarball)

    def generate(self):
        # System dependencies (gmp, mpfr, readline, libxml2) are pre-installed
        # in ~/usr/local. CPPFLAGS is needed for AC_CHECK_HEADER (gmp.h),
        # CFLAGS/CXXFLAGS for compilation, LDFLAGS for linking.
        sys_prefix = os.path.expanduser("~/usr/local")

        env = Environment()
        env.define("PKG_CONFIG_PATH", f"{sys_prefix}/lib/pkgconfig")
        env.define("LD_LIBRARY_PATH", f"{sys_prefix}/lib")
        env.define("CPPFLAGS", f"-I{sys_prefix}/include")
        env.vars(self).save_script("sysdeps_env")

        tc = AutotoolsToolchain(self)
        tc.extra_cflags.append(f"-I{sys_prefix}/include")
        tc.extra_cxxflags.append(f"-I{sys_prefix}/include")
        tc.extra_ldflags.append(f"-L{sys_prefix}/lib")
        tc.configure_args.append("--without-libcurl")
        tc.configure_args.append("--without-icu")
        tc.configure_args.append(f"CPPFLAGS=-I{sys_prefix}/include")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Feature detection: check pthread_cancel availability (R8 compliance).
        # Uses Conan build env (not bare shell vars) to compile a test program.
        # If functions are unavailable (e.g., OHOS), generates an empty header
        # so #ifdef HAVE_PTHREAD_* guards resolve to false.
        test_c = (
            '#include <pthread.h>\n'
            'int main(){pthread_cancel(0);'
            'pthread_setcancelstate(0,0);'
            'pthread_setcanceltype(0,0);return 0;}\n'
        )
        test_file = os.path.join(self.source_folder, "_pthread_test.c")
        header_path = os.path.join(self.source_folder, "libqalculate",
                                   "pthread_compat.h")
        with open(test_file, "w") as f:
            f.write(test_c)

        try:
            self.run(f"$CC -c {test_file} -o /dev/null 2>/dev/null",
                     env="conanbuild")
            with open(header_path, "w") as f:
                f.write("#pragma once\n")
                f.write("#define HAVE_PTHREAD_CANCEL 1\n")
                f.write("#define HAVE_PTHREAD_SETCANCELSTATE 1\n")
                f.write("#define HAVE_PTHREAD_SETCANCELTYPE 1\n")
        except Exception:
            with open(header_path, "w") as f:
                f.write("#pragma once\n")
                f.write("/* pthread_cancel not available on this platform */\n")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["qalculate"]
        self.cpp_info.system_libs = ["gmp", "mpfr", "readline", "xml2"]
