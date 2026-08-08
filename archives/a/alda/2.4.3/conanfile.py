#!/usr/bin/env python3
"""Conan recipe — alda 2.4.3 (Go CLI).

Alda is a text-based music programming language. The client is a Go
binary; the player is a separate Java/Gradle application (not built here).

Build: go generate + CGO_ENABLED=0 go build (static, stripped).
R38: alda is a command-line tool → commands.json declared at software level.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches


class AldaConan(ConanFile):
    name = "alda"
    version = "2.4.3"
    description = "A text-based programming language for music composition"
    license = "EPL-2.0"
    homepage = "https://alda.io"
    url = "https://github.com/alda-lang/alda"

    package_type = "application"
    settings = "os", "arch", "build_type"

    # Go toolchain location (harmonybrew). The Conan build sandbox strips
    # PATH, so we must inject the Go binary directory explicitly.
    _go_bin = os.path.expanduser("~/.harmonybrew/bin")

    # Export patches declared in conandata.yml (none currently).
    def export_sources(self):
        pass

    def layout(self):
        # Source unpacked into self.source_folder.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        client_dir = os.path.join(self.source_folder, "client")
        # CGO_ENABLED=0 → pure static binary (no libc dependency).
        # GOPROXY uses China mirror for reliable module downloads.
        # PATH injection: Conan sandbox strips PATH, Go toolchain unreachable.
        env_prefix = (
            f'CGO_ENABLED=0 '
            f'GOPROXY=https://goproxy.cn,direct '
            f'PATH={self._go_bin}:$PATH '
        )
        # Run go generate to produce generated/version.go.
        self.run(env_prefix + 'go generate ./...', cwd=client_dir)
        # Build the static CLI binary.
        self.run(env_prefix + 'go build -ldflags="-s -w" -o alda .', cwd=client_dir)

    def package(self):
        # Install the binary into bin/.
        copy(
            self,
            "alda",
            src=os.path.join(self.source_folder, "client"),
            dst=os.path.join(self.package_folder, "bin"),
        )

    def package_info(self):
        # Application: expose bin/ so consumers can run alda.
        self.cpp_info.bindirs = ["bin"]
