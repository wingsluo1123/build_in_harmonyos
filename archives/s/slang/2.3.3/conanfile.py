#!/usr/bin/env python3
"""Conan recipe — slang 2.3.3 (S-Lang library + slsh interpreter).

Built with Autotools (configure + make). Slang does not support
out-of-source builds, so configure is run in-source via self.run().
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class SlangConan(ConanFile):
    name = "slang"
    version = "2.3.3"
    description = "S-Lang is a multi-platform programmer's library designed to allow a developer to create robust multi-platform software."
    license = "GPL-2.0-or-later"
    homepage = "https://www.jedsoft.org/slang/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # Slang does not support out-of-source builds (configure rejects
        # $srcdir != "."). The Autotools helper calls configure via an
        # absolute path which makes $srcdir != ".", so we run ./configure
        # manually in-source using the toolchain-generated configure args.
        tmpdir = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        configure_args = autotools._configure_args or ""
        self.run(
            'export TMPDIR="{tmpdir}" && ./configure {args}'.format(
                tmpdir=tmpdir, args=configure_args
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run("make -j2", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # Install from source directory to the Conan package folder
        self.run(
            'make install DESTDIR="{pkg}"'.format(pkg=self.package_folder),
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package_info(self):
        self.cpp_info.libs = ["slang"]
        # Slang builds a shared library; ensure LD_LIBRARY_PATH is set
        # for consumers (OHOS does not get this automatically from VirtualRunEnv)
        self.runenv_info.append_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
