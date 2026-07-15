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
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, copy, export_conandata_patches
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

    def requirements(self):
        # ACL2 requires a host Common Lisp implementation to build.
        # SBCL is the most commonly used; it should be available on the
        # build system (e.g. installed via cmd-pkgs or system package manager).
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Locate the host Lisp compiler.
        lisp = self._find_lisp()

        # Build ACL2 using the host Lisp implementation.
        # 'make large' builds saved_acl2 from scratch.
        self.output.info(f"Building ACL2 with LISP={lisp}")
        self.run(
            f"make large LISP={lisp}",
            cwd=self.source_folder,
            env=["conanbuild"],
        )

        # Verify the executable was created.
        saved_acl2 = os.path.join(self.source_folder, "saved_acl2")
        if not os.path.exists(saved_acl2):
            raise ConanException(
                f"saved_acl2 not found after build at {saved_acl2}"
            )
        self.output.info("ACL2 build complete: saved_acl2 created")

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
        raise ConanInvalidConfiguration(
            "No Common Lisp implementation found. "
            "Install SBCL or CCL before building ACL2. "
            "Try: curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/"
            "releases/download/pkgs/install.sh | sh -s -- sbcl"
        )

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
