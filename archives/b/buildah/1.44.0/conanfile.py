#!/usr/bin/env python3
"""Conan recipe for buildah 1.44.0 — Go-based OCI container image builder."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BuildahConan(ConanFile):
    name = "buildah"
    version = "1.44.0"
    description = "A tool that facilitates building OCI container images"
    license = "Apache-2.0"
    homepage = "https://github.com/containers/buildah"
    url = ""
    package_type = "application"

    settings = "os", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Go environment — HarmonyOS requires tmpfs for Go linker mmap
        tmpdir = os.environ.get("TMPDIR", "/data/storage/el2/base/haps/entry/files")
        go_cache = os.path.join(tmpdir, "go-build")
        gopath = os.path.join(os.path.expanduser("~"), "go")
        os.makedirs(go_cache, exist_ok=True)
        os.makedirs(gopath, exist_ok=True)

        # Set Go environment variables directly (R33: build() must not depend
        # on undefined shell vars; Go compiler is a build tool, not from Conan)
        os.environ["CGO_ENABLED"] = "1"
        os.environ["GOPROXY"] = "https://proxy.golang.org,direct"
        os.environ["GOCACHE"] = go_cache
        os.environ["GOPATH"] = gopath
        os.environ["TMPDIR"] = tmpdir
        os.environ["GOTMPDIR"] = tmpdir

        # Build tags: exclude unavailable platform features
        go_tags = (
            "containers_image_openpgp "
            "exclude_graphdriver_btrfs "
            "exclude_seccomp "
            "exclude_apparmor "
            "no_libsubid "
            "no_systemd "
            "no_sqlite "
            "nolinkednet"
        )

        src = self.source_folder

        # Build entrypoint_arm64 first (needed for embed)
        self.run(
            f'go build -ldflags "-E _start -s" '
            f'-o internal/mkcw/embed/entrypoint_arm64 ./internal/mkcw/embed',
            cwd=src,
        )

        # Compress entrypoint_arm64 to .gz (go:embed requires the .gz file)
        self.run(
            'gzip -k9nf internal/mkcw/embed/entrypoint_arm64',
            cwd=src,
        )

        # Build main buildah binary
        self.run(
            f'go build '
            f'-ldflags "-X main.GitCommit=v{self.version} -X main.buildInfo=1747804800" '
            f'-tags "{go_tags}" '
            f'-o bin/buildah ./cmd/buildah',
            cwd=src,
        )

    def package(self):
        copy(self, "buildah", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        # Bash completion
        completions = os.path.join(self.source_folder, "share", "bash-completion", "completions")
        if os.path.isdir(completions):
            copy(self, "buildah", src=completions,
                 dst=os.path.join(self.package_folder, "share", "bash-completion", "completions"),
                 keep_path=False)
        # License
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
