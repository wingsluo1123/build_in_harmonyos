#!/usr/bin/env python3
"""Conan recipe — numen 0.7 (Go application).

numen is a voice control tool written in Go. It uses `go build` to produce
the `numen` binary and ships a companion `numenc` shell script.

References:
  - install-numen.sh upstream build script
  - R26: static linking (CGO_ENABLED=1 with static libs)
  - R38: commands.json required for application packages
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class NumenConan(ConanFile):
    name = "numen"
    version = "0.7"
    description = "Voice control tool for hands-free computing"
    license = "MIT"
    homepage = "https://git.sr.ht/~geb/numen"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # R38: application package → commands.json required
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Mirror install-numen.sh: go build with version ldflag.
        # CGO is required because vosk-api Go binding links libvosk C++.
        version = str(self.version)
        ldflags = f"-X main.Version={version}"
        # Go environment (based on yamlfmt lessons learned E081/E082):
        # - CGO_ENABLED=1: vosk-api Go binding requires CGO
        # - GOTOOLCHAIN=local: prevent auto-download of unsigned Go toolchain
        # - GOPROXY: use China mirror for module downloads
        # Note: Conan 2.x run() env param must be a list of env-file names,
        # not a dict; set Go vars directly on os.environ instead.
        os.environ.setdefault("CGO_ENABLED", "1")
        os.environ.setdefault("GO111MODULE", "on")
        os.environ.setdefault("GOTOOLCHAIN", "local")
        os.environ.setdefault("GOPROXY", "https://goproxy.cn,direct")
        self.run(
            f'go build -ldflags "{ldflags}" -o numen .',
            cwd=self.source_folder,
        )

    def package(self):
        # Install binaries into bin/ (R38: application bindirs)
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        # Main binary produced by go build
        copy(self, "numen", src=self.source_folder, dst=bindir)
        # Companion shell script shipped in upstream source
        copy(self, "numenc", src=self.source_folder, dst=bindir)

    def package_info(self):
        # Application package: expose bindirs so consumers can locate `numen`.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
