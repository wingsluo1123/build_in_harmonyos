#!/usr/bin/env python3
"""Conan recipe for git-lfs 3.7.0 — Go build.

git-lfs is a Git extension for versioning large files. It is a Go program
that produces a single static binary. This recipe builds it using the Go
toolchain with CGO disabled for a fully static binary.

Key adaptation points:
  - Installs Go toolchain via Harmonybrew if not available on the system.
  - go:generate directives create temporary binaries that cannot execute
    on HarmonyOS without ELF signing. Stub generated files are created in
    build() to skip go generate.
  - -buildvcs=false to avoid git VCS stamping (source from tarball, not git repo).
  - GOTMPDIR set to a writable path that supports mmap (required by Go linker).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class GitLfsConan(ConanFile):
    name = "git-lfs"
    version = "3.7.0"
    description = "Git extension for versioning large files"
    license = "MIT"
    homepage = "https://git-lfs.github.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_go(self):
        """Ensure Go toolchain is available. Install via Harmonybrew if needed."""
        # Try system go first
        go_bin = shutil.which("go")
        if go_bin:
            return go_bin, ""

        # Try Harmonybrew
        brew_bin = "/storage/Users/currentUser/.harmonybrew/bin/brew"
        if not os.path.isfile(brew_bin):
            # Install Harmonybrew using self.run (uses Conan's shell/PATH)
            self.output.info("Installing Harmonybrew for Go toolchain...")
            self.run(
                'curl -fsSL https://harmonybrew.atomgit.com/install.sh | /usr/bin/zsh -',
            )

        # Install Go via brew
        self.output.info("Installing Go via Harmonybrew...")
        self.run(f'{brew_bin} install go')

        # Locate Go
        result = subprocess.run(
            ["bash", "-c", f"{brew_bin} --prefix go"],
            capture_output=True, text=True
        )
        go_prefix = result.stdout.strip()
        goroot = os.path.join(go_prefix, "libexec")
        go_bin = os.path.join(goroot, "bin", "go")
        return go_bin, goroot

    def build(self):
        apply_conandata_patches(self)

        # Create stub generated files to skip go generate.
        # go generate normally runs mangen.go and trgen.go which produce
        # temporary binaries that cannot execute on HarmonyOS without ELF signing.
        mancontent_gen = os.path.join(self.source_folder, "commands", "mancontent_gen.go")
        with open(mancontent_gen, "w") as f:
            f.write("package commands\n\n")
            f.write("func init() {\n")
            f.write("\t// THIS FILE IS GENERATED, DO NOT EDIT\n")
            f.write("\t// Use 'go generate ./commands' to update\n")
            f.write("}\n")

        tr_gen = os.path.join(self.source_folder, "tr", "tr_gen.go")
        with open(tr_gen, "w") as f:
            f.write("package tr\n\n")
            f.write("func init() {\n")
            f.write("\t// THIS FILE IS GENERATED, DO NOT EDIT\n")
            f.write("\t// Use 'go generate ./tr/trgen' to update\n")
            f.write("}\n")

        # Ensure Go toolchain is available
        go_bin, goroot = self._ensure_go()

        # Set up Go environment for HarmonyOS
        gocache = os.path.join(self.build_folder, ".gocache")
        gotmpdir = os.path.join(self.build_folder, ".gotmpdir")
        gopath = os.path.join(self.build_folder, ".gopath")
        os.makedirs(gocache, exist_ok=True)
        os.makedirs(gotmpdir, exist_ok=True)
        os.makedirs(gopath, exist_ok=True)

        # Build env as list of "VAR=value" strings (Conan 2.x requirement)
        path = os.environ.get("PATH", "")
        if goroot:
            path = os.path.join(goroot, "bin") + os.pathsep + path
        path = os.path.join(gopath, "bin") + os.pathsep + path

        env = [
            "GOPROXY=https://goproxy.cn,https://goproxy.io,direct",
            "GO111MODULE=on",
            "CGO_ENABLED=0",
            "GOTOOLCHAIN=local",
            f"GOCACHE={gocache}",
            f"GOTMPDIR={gotmpdir}",
            f"GOPATH={gopath}",
            f"PATH={path}",
        ]
        if goroot:
            env.append(f"GOROOT={goroot}")

        # Download Go module dependencies
        self.run(f'"{go_bin}" mod download', cwd=self.source_folder, env=env)

        # Build git-lfs binary
        ldflags = "-X github.com/git-lfs/git-lfs/v3/config.GitCommit=v3.7.0 -s -w"
        self.run(
            f'"{go_bin}" build -buildvcs=false -o git-lfs -ldflags "{ldflags}" .',
            cwd=self.source_folder,
            env=env,
        )

    def package(self):
        copy(
            self,
            "git-lfs",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
