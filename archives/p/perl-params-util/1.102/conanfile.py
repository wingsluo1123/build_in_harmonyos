#!/usr/bin/env python3
"""Conan recipe for perl-params-util — Perl XS module (Makefile.PL + XS).

Build system: perl Makefile.PL + make + make install
XS module: Util.xs → Util.c → Util.so
Has pure Perl fallback (Params::Util::PP) activated via PERL_PARAMS_UTIL_PP=1.

On OHOS:
  - musl C library headers at $MUSL_PREFIX/include (sys/types.h etc.)
  - musl libc at $MUSL_PREFIX/lib
  - CRT workaround: -nostartfiles -nodefaultlibs -lc
  - XS .so may fail to load at runtime due to ELF signing (pure Perl fallback works)
"""
import os
import re

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PerlparamsutilConan(ConanFile):
    name = "perl-params-util"
    version = "1.102"
    description = "Simple, compact and correct param-checking functions (Perl XS module)"
    license = "MIT"
    homepage = "https://metacpan.org/dist/Params-Util"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        import hashlib
        import tarfile

        sources = self.conan_data["sources"]
        url = sources["url"]
        expected_sha256 = sources["sha256"]
        filename = url.split("/")[-1]

        # Download using curl — Python's urllib lacks SSL on CI
        tarball = os.path.join(self.source_folder, filename)
        self.run(f'curl -sL "{url}" -o "{tarball}"')

        # Verify SHA256
        h = hashlib.sha256()
        with open(tarball, "rb") as f:
            h.update(f.read())
        if h.hexdigest() != expected_sha256:
            raise Exception(f"SHA256 mismatch: expected {expected_sha256}, got {h.hexdigest()}")

        # Extract with strip_root (remove top-level directory)
        with tarfile.open(tarball, "r:*") as tar:
            members = tar.getmembers()
            top = members[0].name.split("/")[0]
            for m in members:
                if m.name == top:
                    continue
                m.name = m.name[len(top) + 1:]
                tar.extract(m, self.source_folder)

        # Clean up tarball
        os.remove(tarball)

    def build(self):
        # Apply conandata patches (if any)
        apply_conandata_patches(self)

        # Step 1: Generate Makefile via Makefile.PL
        # XS detection may fail due to ld.lld not supporting -fstack-protector-strong,
        # but ExtUtils::MakeMaker still generates xsubpp rules for .xs files.
        self.run("perl Makefile.PL", cwd=self.source_folder)

        # Step 2: Patch Makefile for OpenHarmony platform
        #   a) Add musl C library include path for system headers (sys/types.h etc.)
        #   b) Add CRT workaround: -nostartfiles -nodefaultlibs -lc
        #   c) Add musl lib path for finding libc
        makefile_path = os.path.join(self.source_folder, "Makefile")
        with open(makefile_path, "r") as f:
            content = f.read()

        musl_prefix = os.environ.get("MUSL_PREFIX")
        if not musl_prefix:
            raise Exception("MUSL_PREFIX environment variable must be set to musl C library prefix")
        musl_inc = os.path.join(musl_prefix, "include")
        musl_lib = os.path.join(musl_prefix, "lib")

        # Add musl include path to CCFLAGS (idempotent: skip if already present)
        content = re.sub(
            r"^(CCFLAGS = )(?!.*" + re.escape(musl_inc) + ")",
            rf"\1-I{musl_inc} ",
            content,
            flags=re.MULTILINE,
        )
        # Add CRT workaround and musl lib path to LDDLFLAGS (idempotent: skip if already present)
        content = re.sub(
            r"^(LDDLFLAGS = -shared)(?!.*-nostartfiles)(.*)$",
            rf"\1 -nostartfiles -nodefaultlibs -L{musl_lib} -lc\2",
            content,
            flags=re.MULTILINE,
        )

        with open(makefile_path, "w") as f:
            f.write(content)

        # Step 3: Build (R9: use -j1)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Install with DESTDIR to package folder
        dest = os.path.join(self.package_folder, "")
        self.run(f"make install DESTDIR={dest}", cwd=self.source_folder)

        # Also copy .so to standard lib/ for package integrity checks
        import glob
        import shutil
        so_matches = glob.glob(
            os.path.join(dest, "**", "auto", "Params", "Util", "Util.so"),
            recursive=True,
        )
        lib_dst = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dst, exist_ok=True)
        if so_matches:
            shutil.copy2(so_matches[0], os.path.join(lib_dst, "Util.so"))
        else:
            self.output.warn("Util.so not found in install output; XS module may not be available")

    def package_info(self):
        # Perl XS module — loaded at runtime by Perl's DynaLoader,
        # not a C/C++ link library; no cpp_info declarations needed.
        pass
