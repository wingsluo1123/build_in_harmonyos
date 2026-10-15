#!/usr/bin/env python3
"""Conan recipe for mrbuild 1.17.

mrbuild is a pure file-distribution package: GNU Makefile boilerplate
(Makefile.common.header / Makefile.common.footer) plus the Perl helper
script bin/make-pod-from-help, README.org and build_examples/. Nothing is
compiled; build() applies the portability patch and sanity-checks the
payload, package() installs the files.
"""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MrbuildConan(ConanFile):
    name = "mrbuild"
    version = "1.17"
    description = ("GNU Makefile build-system boilerplate (Makefile.common."
                   "header/footer) and the make-pod-from-help helper script")
    license = "MIT"
    homepage = "https://github.com/dkogan/mrbuild"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mrbuild is adapted for Linux and OHOS only")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Pure file distribution: there is nothing to compile. Sanity-check
        # that the payload we are about to ship is complete.
        required = (
            "Makefile.common.header",
            "Makefile.common.footer",
            os.path.join("bin", "make-pod-from-help"),
            "README.org",
            os.path.join("build_examples", "GNU_Make", "Makefile"),
        )
        for rel in required:
            path = os.path.join(self.source_folder, rel)
            if not os.path.isfile(path):
                raise ConanException("upstream payload incomplete, missing: %s" % rel)
        self.output.info("mrbuild payload complete: pure file distribution, nothing to compile")

    def package(self):
        include_dst = os.path.join(self.package_folder, "include", "mrbuild")
        share_dst = os.path.join(self.package_folder, "share", "mrbuild")
        bin_dst = os.path.join(self.package_folder, "bin")
        copy(self, "Makefile.common.header", src=self.source_folder, dst=include_dst)
        copy(self, "Makefile.common.footer", src=self.source_folder, dst=include_dst)
        copy(self, "make-pod-from-help", src=os.path.join(self.source_folder, "bin"), dst=bin_dst)
        copy(self, "README.org", src=self.source_folder, dst=share_dst)
        copy(self, "build_examples", src=self.source_folder, dst=share_dst)
        os.chmod(os.path.join(bin_dst, "make-pod-from-help"), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include/mrbuild"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        mrbuild_dir = os.path.join(self.package_folder, "include", "mrbuild")
        mrbuild_bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.define_path("MRBUILD_DIR", mrbuild_dir)
        self.buildenv_info.define_path("MRBUILD_BINDIR", mrbuild_bindir)
        self.runenv_info.define_path("MRBUILD_DIR", mrbuild_dir)
        self.runenv_info.define_path("MRBUILD_BINDIR", mrbuild_bindir)
