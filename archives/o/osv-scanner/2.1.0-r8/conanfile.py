#!/usr/bin/env python3
"""Conan recipe for osv-scanner 2.1.0-r8 — Go project.

osv-scanner is a Go vulnerability scanner tool. This recipe builds two
binaries: osv-scanner and osv-reporter, using the Go toolchain.

Key OHOS adaptations:
- Go toolchain must be signed to execute on OHOS (ELF signature requirement)
- fallocate() returns EACCES on HMDFS/tmpfs; use toolexec wrapper to redirect
  linker output to /dev/shm which supports fallocate
- Compiled binaries must be signed with binary-sign-tool
- CGO_ENABLED=0 for pure Go compilation (no C dependencies)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.errors import ConanInvalidConfiguration


class OsvScannerConan(ConanFile):
    name = "osv-scanner"
    version = "2.1.0-r8"
    description = "Vulnerability scanner that checks OSV database for dependencies"
    license = "Apache-2.0"
    homepage = "https://github.com/google/osv-scanner"
    url = ""  # CI fills this

    # Go application — pure binary, no shared libraries
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        # R32: settings.os must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.settings.os} not supported. Only Linux and OHOS are supported."
            )
        # Validate architecture — GOARCH is derived from settings.arch
        arch = str(self.settings.arch)
        if arch not in ("armv8", "x86_64"):
            raise ConanInvalidConfiguration(
                f"Unsupported architecture: {arch}. Only armv8 and x86_64 are supported."
            )

    def generate(self):
        # Go project — no CMake/Autotools toolchain needed
        pass

    def build(self):
        # Apply patches from conandata.yml (R2: patch pipeline)
        apply_conandata_patches(self)

        # Set up Go environment as list of KEY=VALUE strings (Conan 2.x API)
        goroot = os.environ.get("GOROOT", "")
        go_bin = os.environ.get("GO_BIN_PATH", "")
        if not goroot or not go_bin:
            raise ConanInvalidConfiguration(
                "GOROOT and GO_BIN_PATH environment variables must be set. "
                "Please configure the Go toolchain path."
            )
        gopath = os.environ.get("GOPATH", os.path.join(os.path.expanduser("~"), "go"))
        goproxy = os.environ.get("GOPROXY", "https://goproxy.cn,direct")
        tmpdir = os.environ.get("TMPDIR", os.path.join(os.path.expanduser("~"), "tmp"))
        gocache = os.environ.get("GOCACHE", os.path.join(tmpdir, "go-cache"))
        gotmpdir = os.environ.get("GOTMPDIR", os.path.join(tmpdir, "go-tmp"))

        env_list = [
            f"GOROOT={goroot}",
            f"PATH={go_bin}:{os.environ.get('PATH', '')}",
            f"GOPATH={gopath}",
            f"GOPROXY={goproxy}",
            f"TMPDIR={tmpdir}",
            f"GOCACHE={gocache}",
            f"GOTMPDIR={gotmpdir}",
            "GOOS=linux",
            f"GOARCH={'arm64' if str(self.settings.arch) == 'armv8' else 'amd64'}",
            "CGO_ENABLED=0",
        ]

        # Create required directories
        for d in [gopath, tmpdir, gocache, gotmpdir]:
            os.makedirs(d, exist_ok=True)

        build_dir = self.source_folder

        # Download dependencies
        self.run('go mod download', env=env_list, cwd=build_dir)

        # toolexec wrapper is required on OHOS (fallocate workaround)
        toolexec_arg = ""
        if str(self.settings.os) == "OHOS":
            toolexec_script = os.environ.get(
                "TOOLEXEC_WRAPPER",
                os.path.join(os.path.expanduser("~"), "tmp", "toolexec_wrapper.sh")
            )
            if not os.path.exists(toolexec_script):
                raise ConanInvalidConfiguration(
                    f"toolexec wrapper not found at {toolexec_script}. "
                    f"It is required on OHOS for Go compilation. "
                    f"Set TOOLEXEC_WRAPPER env var to specify its path."
                )
            toolexec_arg = f"-toolexec {toolexec_script}"

        # Build osv-scanner
        self.run(f'go build {toolexec_arg} -o osv-scanner ./cmd/osv-scanner/', env=env_list, cwd=build_dir)

        # Build osv-reporter
        self.run(f'go build {toolexec_arg} -o osv-reporter ./cmd/osv-reporter/', env=env_list, cwd=build_dir)

        # Sign binaries on OHOS (ELF signature requirement)
        if str(self.settings.os) == "OHOS":
            sign_tool = os.environ.get(
                "SIGN_TOOL_PATH", "/data/service/hnp/bin/binary-sign-tool"
            )
            if not os.path.exists(sign_tool):
                raise ConanInvalidConfiguration(
                    f"binary-sign-tool not found at {sign_tool}. "
                    f"ELF signature is required on OHOS. "
                    f"Set SIGN_TOOL_PATH env var to specify its path."
                )
            for binary in ["osv-scanner", "osv-reporter"]:
                signed = f"{binary}-signed"
                self.run(
                    f'{sign_tool} sign -inFile {binary} -outFile {signed} '
                    f'-selfSign 1 -signAlg SHA256withECDSA',
                    env=env_list, cwd=build_dir
                )
                # Replace unsigned with signed
                os.remove(os.path.join(build_dir, binary))
                shutil.move(
                    os.path.join(build_dir, signed),
                    os.path.join(build_dir, binary)
                )
                os.chmod(os.path.join(build_dir, binary), 0o755)

    def package(self):
        # Copy both binaries to bin/ (binaries are built in source_folder)
        copy(self, "osv-scanner", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "osv-reporter", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Pure Go binary application — no shared libraries
        self.cpp_info.libs = []
        # Add bin/ to bindirs for consumers (Conan 2.x API)
        self.cpp_info.bindirs = ["bin"]
