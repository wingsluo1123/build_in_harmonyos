#!/usr/bin/env python3
"""Conan recipe for buildah 1.44.0 — Go-based OCI container image builder."""
import os
import subprocess

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
        tmpdir = os.environ.get("TMPDIR", "/tmp")
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
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)

        # Copy binary
        buildah_bin = os.path.join(self.source_folder, "bin", "buildah")
        copy(self, "buildah", src=os.path.join(self.source_folder, "bin"),
             dst=bindir, keep_path=False)

        # ELF signing for HarmonyOS (allows binary execution)
        pkg_bin = os.path.join(bindir, "buildah")
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.isfile(sign_tool) and os.path.isfile(objcopy):
            # Remove old signature
            subprocess.run([objcopy, "--remove-section", ".codesign", pkg_bin],
                         capture_output=True, timeout=10)
            # Sign binary
            tmp_signed = pkg_bin + ".signed.tmp"
            r = subprocess.run(
                [sign_tool, "sign", "-inFile", pkg_bin,
                 "-outFile", tmp_signed, "-selfSign", "1"],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0 and os.path.isfile(tmp_signed):
                os.replace(tmp_signed, pkg_bin)
            else:
                # Non-blocking: signing may not be available on all platforms
                if os.path.isfile(tmp_signed):
                    os.unlink(tmp_signed)

        os.chmod(pkg_bin, 0o755)

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
