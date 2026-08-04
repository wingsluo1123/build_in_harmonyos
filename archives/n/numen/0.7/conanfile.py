#!/usr/bin/env python3
"""Conan recipe — numen 0.7 (Go application).

numen is a voice control tool written in Go. It uses `go build` to produce
the `numen` binary and ships a companion `numenc` shell script.

The recipe auto-downloads the Go SDK when `go` is not in PATH, since the
HarmonyOS CI environment does not include a Go toolchain (E-draft-2699).

References:
  - install-numen.sh upstream build script
  - R26: static linking (CGO_ENABLED=1 with static libs)
  - R38: commands.json required for application packages
  - E081: Go linker mmap fails on HMDFS — output to TMPDIR
  - E082: GOTOOLCHAIN=local prevents auto-download of unsigned Go toolchain
"""
import os
import shutil

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

    def validate(self):
        # Override base-class validation: this recipe auto-downloads the Go
        # SDK in build() when `go` is not in PATH, so we do not need the
        # toolchain to be pre-installed on the CI worker (E-draft-2699).
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # ── Ensure Go toolchain is available ──
        # HarmonyOS CI does not include Go in PATH. Download the Go SDK
        # binary release and set up GOROOT/PATH (E-draft-2699).
        if not shutil.which("go"):
            self.output.info("Go not found in PATH — downloading Go SDK...")
            # Use TMPDIR (hmfs) for extraction — HMDFS may reject mmap writes
            tmpdir = os.environ.get("TMPDIR", "/tmp")
            go_sdk_dir = os.path.join(tmpdir, "numen_go_sdk")
            get(
                self,
                url=self.conan_data["go_toolchain"]["url"],
                sha256=self.conan_data["go_toolchain"]["sha256"],
                destination=go_sdk_dir,
                strip_root=True,
            )
            os.environ["GOROOT"] = go_sdk_dir
            os.environ["PATH"] = (
                os.path.join(go_sdk_dir, "bin")
                + os.pathsep
                + os.environ.get("PATH", "")
            )
            self.output.info(f"Go SDK ready at {go_sdk_dir}")

        # Mirror install-numen.sh: go build with version ldflag.
        # CGO is required because vosk-api Go binding links libvosk C++.
        version = str(self.version)
        ldflags = f"-X main.Version={version}"
        # Go environment (based on yamlfmt lessons learned E081/E082):
        # - CGO_ENABLED=1: vosk-api Go binding requires CGO
        # - GOTOOLCHAIN=local: prevent auto-download of unsigned Go toolchain
        # - GOPROXY: use China mirror for module downloads
        os.environ.setdefault("CGO_ENABLED", "1")
        os.environ.setdefault("GO111MODULE", "on")
        os.environ.setdefault("GOTOOLCHAIN", "local")
        os.environ.setdefault("GOPROXY", "https://goproxy.cn,direct")

        # E081: Go linker mmap fails on HMDFS — write output to TMPDIR
        # (hmfs filesystem) instead of source_folder (HMDFS).
        tmpdir = os.environ.get("TMPDIR", "/tmp")
        output_bin = os.path.join(tmpdir, "numen")
        self._numen_output = output_bin

        self.run(
            f'go build -ldflags "{ldflags}" -o {output_bin} .',
            cwd=self.source_folder,
        )

    def package(self):
        # Install binaries into bin/ (R38: application bindirs)
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        # Main binary (built to TMPDIR to avoid HMDFS mmap issue E081)
        numen_src = getattr(self, "_numen_output", None)
        if numen_src and os.path.isfile(numen_src):
            copy(self, "numen", src=os.path.dirname(numen_src), dst=bindir)
        else:
            # Fallback: try source_folder
            copy(self, "numen", src=self.source_folder, dst=bindir)
        # Companion shell script shipped in upstream source
        copy(self, "numenc", src=self.source_folder, dst=bindir)

    def package_info(self):
        # Application package: expose bindirs so consumers can locate `numen`.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
