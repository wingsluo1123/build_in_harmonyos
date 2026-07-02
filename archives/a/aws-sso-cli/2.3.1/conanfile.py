#!/usr/bin/env python3
"""Conan recipe — aws-sso-cli 2.3.1 (Go project, custom build).

Build system: Go (custom), not autotools/cmake.
Cross-compiles with CGO_ENABLED=0 for OHOS aarch64.
"""
import os
import hashlib
import tarfile
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, apply_conandata_patches, export_conandata_patches


class AwsSsoCliConan(ConanFile):
    name = "aws-sso-cli"
    version = "2.3.1"
    description = "Securely manage AWS API credentials using AWS SSO"
    license = "GPL-3.0-only"
    homepage = "https://github.com/synfinatic/aws-sso-cli"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # Go compiler path (harmonybrew installed)
    go_root = "/storage/Users/currentUser/.harmonybrew/Cellar/go/1.26.4_4/libexec"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # No external dependencies; Go modules are self-contained

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS"
            )

    def layout(self):
        self.folders.build = "."

    def source(self):
        src = self.conan_data["sources"]
        sha256_expected = src["sha256"]
        archive = os.path.join(self.source_folder, "aws-sso-cli-2.3.1.tar.gz")
        
        # Try local cached copy first (pre-downloaded due to OHOS SSL issues)
        local_cache = "/data/storage/el2/base/cache/aws-sso-cli-v2.3.1.tar.gz"
        local_build = os.path.expanduser("~/tmp/builds/aws-sso-cli-2.3.1.tar.gz")
        
        if os.path.exists(local_cache):
            shutil.copy2(local_cache, archive)
        elif os.path.exists(local_build):
            shutil.copy2(local_build, archive)
        else:
            # Fallback: try curl with mirror
            url = src["url"]
            mirror = "https://gh-proxy.com/" + url
            self.run(f'curl -kL --connect-timeout 30 -o "{archive}" "{mirror}"')
        
        # Verify SHA256
        with open(archive, "rb") as f:
            sha256_actual = hashlib.sha256(f.read()).hexdigest()
        if sha256_actual != sha256_expected:
            raise Exception(f"SHA256 mismatch: expected {sha256_expected}, got {sha256_actual}")
        
        # Extract with strip_root
        with tarfile.open(archive, "r:gz") as tar:
            members = tar.getmembers()
            if members:
                root_dir = members[0].name.split("/")[0]
                for m in members:
                    if m.name.startswith(root_dir + "/"):
                        m.name = m.name[len(root_dir) + 1:]
                    elif m.name == root_dir:
                        continue
                tar.extractall(path=self.source_folder)
        os.remove(archive)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        go_bin = os.path.join(self.go_root, "bin", "go")
        # Set Go build environment variables directly
        env_list = [
            f"CGO_ENABLED=0",
            f"GOOS=linux",
            f"GOARCH=arm64",
            f"GOROOT={self.go_root}",
            f"GOPROXY=https://goproxy.cn,direct",
            f"TMPDIR=/data/storage/el2/base/cache",
            f"PATH={os.path.join(self.go_root, 'bin')}:{os.environ.get('PATH', '')}",
        ]
        self.run(
            f'{go_bin} build -trimpath '
            f'-ldflags=\'-s -w -X "main.Version=2.3.1" -X "main.Tag=v2.3.1"\' '
            f'-o aws-sso ./cmd/aws-sso/...',
            env=env_list,
        )

    def package(self):
        copy(self, "aws-sso", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bins = ["aws-sso"]
        self.cpp_info.libs = []
