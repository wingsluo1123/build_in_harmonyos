#!/usr/bin/env python3
"""Conan recipe — pandoc 3.10 (Haskell/Cabal build system).

pandoc is a Haskell application that requires GHC to compile.
Build system: Cabal (pandoc.cabal, build-type: Simple)
License: GPL-2.0-or-later
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class PandocConan(ConanFile):
    name = "pandoc"
    version = "3.10"
    description = "Swiss-army knife of markup format conversion"
    license = "GPL-2.0-or-later"
    homepage = "https://pandoc.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # GHC is required to compile Haskell source code
        # Currently not available as a Conan package on OpenHarmony
        self.requires("ghc/9.10.3@ohpcd/stable")
        self.requires("gmp/6.3.0@ohpcd/stable")

    def validate(self):
        # R32: Platform guard — pandoc only supports Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Cabal build system does not use AutotoolsToolchain
        # GHC and Cabal configuration is handled by cabal-install
        pass

    def build(self):
        apply_conandata_patches(self)
        # Haskell/Cabal build commands:
        #   cabal update
        #   cabal configure --prefix=$PREFIX
        #   cabal build
        #   cabal install
        # Note: GHC must be available in PATH for these commands to work
        self.run("cabal configure --prefix={}".format(self.package_folder), env="conanbuild")
        self.run("cabal build", env="conanbuild")

    def package(self):
        # Install the built pandoc executable
        self.run("cabal install --prefix={}".format(self.package_folder), env="conanbuild")
        # Copy data files
        copy(self, "*.yaml", src=self.build_folder, dst=os.path.join(self.package_folder, "share", "pandoc"))

    def package_info(self):
        # pandoc is a command-line tool (executable), not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
