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
    settings = "os", "compiler", "build_type", "arch"

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
        # Inject Go toolchain into the *process* environment so that
        # Conan's self.run (which re-execs via env) inherits it. Shell-string
        # `PATH=...:$PATH` doesn't work because Conan's run sandbox strips
        # PATH before the shell expands $PATH.
        os.environ["PATH"] = self._go_bin + ":" + os.environ.get("PATH", "")
        os.environ["CGO_ENABLED"] = "0"
        os.environ.setdefault("GOPROXY", "https://goproxy.cn,direct")
        # Run go generate to produce generated/version.go.
        self.run("go generate ./...", cwd=client_dir)
        # Build the static CLI binary.
        self.run('go build -ldflags="-s -w" -o alda .', cwd=client_dir)

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
