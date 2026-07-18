#!/usr/bin/env python3
"""Conan recipe — acl2 8.7

ACL2 (A Computational Logic for Applicative Common Lisp) is a theorem
prover and a logic for reasoning about programs written in a subset of
Common Lisp.  It is built on top of a host Common Lisp implementation
(SBCL by default; CCL is also supported).

Build system: GNU Make (GNUmakefile)
Homepage: https://github.com/acl2/acl2
License: ACL2 License (BSD-like)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class Acl2Conan(ConanFile):
    name = "acl2"
    version = "8.7"
    description = "ACL2 — A Computational Logic for Applicative Common Lisp (theorem prover)"
    license = "ACL2 License"
    homepage = "https://github.com/acl2/acl2"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "gcl-sign-elf.sh"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os must be Linux or OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported, requires Linux or OHOS"
            )

    def source(self):
        sources = self.conan_data["sources"]
        urls = [sources["url"]] + list(sources.get("backup_urls", []))
        last_error = None
        for url in urls:
            try:
                get(self, url=url, sha256=sources["sha256"], strip_root=True)
                return
            except Exception as e:
                last_error = e
                self.output.warning(f"Download failed from {url}, trying next mirror...")
        raise ConanException(f"All download URLs failed. Last error: {last_error}")

    def build(self):
        # Locate the host Lisp compiler.
        lisp = self._find_lisp()

        if not lisp:
            lisp = self._build_gcl()

        # Build ACL2 using the host Lisp implementation.
        # 'make large' builds saved_acl2 from scratch.
        self.output.info(f"Building ACL2 with LISP={lisp}")
        self.run(
            f'MAKEFLAGS=-j1 make -j1 large LISP="{lisp}"',
            cwd=self.source_folder,
            env=["conanbuild"],
        )

        # Verify the executable was created.
        saved_acl2 = os.path.join(self.source_folder, "saved_acl2")
        if not os.path.exists(saved_acl2):
            raise ConanException(
                f"saved_acl2 not found after build at {saved_acl2}"
            )
        self._sign_elf(saved_acl2)
        self.output.info("ACL2 build complete: saved_acl2 created")

    def _build_gcl(self):
        gcl = self.conan_data["build_sources"]["gcl"]
        gcl_folder = os.path.join(self.build_folder, "gcl")
        self._download(gcl, gcl_folder)
        apply_conandata_patches(self, base_path=gcl_folder)
        sign_command = "true"
        if self.settings.os == "OHOS":
            sign_script = os.path.join(self.export_sources_folder, "gcl-sign-elf.sh")
            sign_command = f"/data/service/hnp/bin/bash {sign_script}"
        self.run(
            "./configure --enable-ansi=yes --enable-xgcl=no --enable-readline=no "
            "--enable-dynsysgmp=no --enable-locbfd=yes --disable-statsysbfd",
            cwd=gcl_folder,
            env=["conanbuild"],
        )
        self.run(
            f'MAKEFLAGS=-j1 make -j1 SIGN_ELF="{sign_command}"',
            cwd=gcl_folder,
            env=["conanbuild"],
        )
        gcl_binary = os.path.join(gcl_folder, "unixport", "saved_gcl")
        if not os.path.exists(gcl_binary):
            raise ConanException(f"GCL bootstrap failed: {gcl_binary} was not created")
        return gcl_binary

    def _download(self, source, destination):
        urls = [source["url"]] + list(source.get("backup_urls", []))
        last_error = None
        for url in urls:
            try:
                get(
                    self,
                    url=url,
                    sha256=source["sha256"],
                    destination=destination,
                    strip_root=True,
                )
                return
            except Exception as e:
                last_error = e
                self.output.warning(f"Download failed from {url}, trying next mirror...")
        raise ConanException(f"All download URLs failed. Last error: {last_error}")

    def _sign_elf(self, path):
        if self.settings.os != "OHOS":
            return
        script = os.path.join(self.export_sources_folder, "gcl-sign-elf.sh")
        self.run(f'/data/service/hnp/bin/bash "{script}" "{path}"')

    def _find_lisp(self):
        """Locate a Common Lisp implementation on the system."""
        for candidate in ("sbcl", "ccl", "lisp"):
            path = shutil.which(candidate)
            if path:
                self.output.info(f"Found Lisp compiler: {candidate} at {path}")
                return candidate
        # Fallback: check common install prefix on OHOS
        prefix = os.path.expanduser("~/usr/local")
        for candidate in ("sbcl", "ccl"):
            p = os.path.join(prefix, "bin", candidate)
            if os.path.exists(p):
                self.output.info(f"Found Lisp compiler: {candidate} at {p}")
                return p
        return None

    def package(self):
        copy(self, "saved_acl2*", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

        saved_acl2 = os.path.join(self.package_folder, "bin", "saved_acl2")
        if os.path.exists(saved_acl2):
            os.chmod(saved_acl2, 0o755)

    def package_info(self):
        # ACL2 is an application, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
