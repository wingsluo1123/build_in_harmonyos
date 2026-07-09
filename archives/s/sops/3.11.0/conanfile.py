#!/usr/bin/env python3
"""Conan recipe for sops 3.11.0 — Go project (Mozilla SOPS).

SOPS (Secrets OPerationS) is a Go-based tool for editing encrypted files.
Built with `go build` (CGO_ENABLED=0, static binary).

OHOS note: Go binaries are unsigned ELF executables. On OHOS, they require
the `elfldr` wrapper to run. This recipe creates a shell wrapper script
in bin/ that transparently invokes elfldr for the real binary.
"""
import os
import stat

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SopsConan(ConanFile):
    name = "sops"
    version = "3.11.0"
    description = "SOPS - Secrets OPerationS - editor of encrypted files (YAML, JSON, ENV, INI, BINARY)"
    license = "MPL-2.0"
    homepage = "https://github.com/getsops/sops"
    url = ""  # CI fills this

    # Go projects are self-contained; keep settings for profile compatibility
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Go build environment — Conan 2.x requires env as list of "KEY=VALUE" strings
        go_root = os.path.expanduser("~/.goenv/versions/1.24.4")
        go_env = [
            "CGO_ENABLED=0",
            "GO111MODULE=on",
            "GOPROXY=https://goproxy.cn,direct",
            f"GOROOT={go_root}",
            f"PATH={go_root}/bin:{os.environ.get('PATH', '')}",
        ]
        self.run(
            "go build -trimpath -ldflags "
            "'-s -w -X github.com/getsops/sops/v3/version.Version=3.11.0' "
            "-o sops ./cmd/sops",
            env=go_env,
            cwd=self.source_folder,
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)

        # Copy the Go-built binary as sops.real
        copy(self, "sops", src=self.source_folder, dst=bin_dir)
        sops_bin = os.path.join(bin_dir, "sops")
        sops_real = os.path.join(bin_dir, "sops.real")
        if os.path.exists(sops_bin):
            os.rename(sops_bin, sops_real)
            os.chmod(sops_real, 0o755)

        # Create wrapper script for OHOS (unsigned ELF needs elfldr)
        wrapper = "#!/bin/sh\nexec elfldr \"$(dirname \"$0\")/sops.real\" \"$@\"\n"
        with open(sops_bin, "w") as f:
            f.write(wrapper)
        os.chmod(sops_bin, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    def package_info(self):
        # sops is a standalone binary tool, not a library
        self.cpp_info.libs = []
        # Ensure bin/ is in PATH for consumers (test_package, runtime)
        self.cpp_info.bindirs = ["bin"]
