#!/usr/bin/env python3
"""Conan 2.x recipe for Docker CLI 29.5.3.

Docker CLI is the command line tool for Docker container management.
It is written in Go and uses the standard Go module build system with
vendored dependencies.

Build process:
  1. Download and set up Go toolchain (if not available)
  2. Create go.mod/go.sum from vendor.mod/vendor.sum (CalVer repo convention)
  3. Remove unsupported `tool` directive from go.mod
  4. Build with `go build -mod=vendor`
  5. Sign the resulting binary for HarmonyOS

E124: Go linker mmap fails on HMDFS; output to /data partition.
"""
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

SIGN_TOOL = "/data/service/hnp/bin/binary-sign-tool"
OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"


def sign_elf(elf_path):
    """Sign an ELF binary for HarmonyOS using binary-sign-tool."""
    if not os.path.isfile(SIGN_TOOL):
        return False
    tmp = elf_path + ".signed.tmp"
    subprocess.run([OBJCOPY, "--remove-section", ".codesign", elf_path],
                   capture_output=True, timeout=10)
    for _ in range(3):
        r = subprocess.run(
            [SIGN_TOOL, "sign", "-inFile", elf_path,
             "-outFile", tmp, "-selfSign", "1"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0 and os.path.isfile(tmp):
            shutil.move(tmp, elf_path)
            os.chmod(elf_path, 0o755)
            return True
        import time; time.sleep(1)
    if os.path.isfile(tmp):
        os.unlink(tmp)
    return False


class DockerCliConan(ConanFile):
    name = "docker"
    version = "29.5.3"
    description = "Docker CLI - the command line tool for Docker container management"
    license = "Apache-2.0"
    homepage = "https://www.docker.com"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _setup_go(self):
        """Download and set up Go toolchain if not available."""
        go_bin = shutil.which("go")
        if go_bin:
            return go_bin

        go_version = "1.25.0"
        go_url = f"https://dl.google.com/go/go{go_version}.linux-arm64.tar.gz"
        tmpdir = os.environ.get("TMPDIR", "/tmp")
        go_tarball = os.path.join(tmpdir, f"go{go_version}.tar.gz")
        goroot = os.path.join(tmpdir, "golang", "go")

        if not os.path.isdir(goroot):
            os.makedirs(os.path.dirname(goroot), exist_ok=True)
            self.run(f'curl -fSL --connect-timeout 30 --max-time 600 -o "{go_tarball}" "{go_url}"')
            self.run(f'mkdir -p "{os.path.dirname(goroot)}" && tar xzf "{go_tarball}" -C "{os.path.dirname(goroot)}"')

        # Sign Go ELF binaries for HarmonyOS
        for root, dirs, files in os.walk(goroot):
            for f in files:
                fpath = os.path.join(root, f)
                try:
                    with open(fpath, "rb") as fp:
                        if fp.read(4) == b"\x7fELF":
                            sign_elf(fpath)
                except Exception:
                    pass

        os.environ["GOROOT"] = goroot
        os.environ["PATH"] = os.path.join(goroot, "bin") + ":" + os.environ.get("PATH", "")
        return os.path.join(goroot, "bin", "go")

    def build(self):
        apply_conandata_patches(self)

        # R32: settings.os must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"docker only supports Linux/OHOS, got {self.settings.os}"
            )

        # Set up Go toolchain
        self._setup_go()

        # Create go.mod from vendor.mod (CalVer repo convention)
        src = self.source_folder
        vendor_mod = os.path.join(src, "vendor.mod")
        go_mod = os.path.join(src, "go.mod")
        if os.path.isfile(vendor_mod) and not os.path.isfile(go_mod):
            shutil.copy(vendor_mod, go_mod)

        vendor_sum = os.path.join(src, "vendor.sum")
        go_sum = os.path.join(src, "go.sum")
        if os.path.isfile(vendor_sum) and not os.path.isfile(go_sum):
            shutil.copy(vendor_sum, go_sum)

        # Remove unsupported `tool` directive from go.mod
        if os.path.isfile(go_mod):
            with open(go_mod, "r") as f:
                lines = f.readlines()
            with open(go_mod, "w") as f:
                for line in lines:
                    if not line.startswith("tool "):
                        f.write(line)

        # E124: Go linker mmap fails on HMDFS; use /data partition for output
        writable_tmp = "/data/storage/el2/base/haps/entry/temp"
        if not os.path.isdir(writable_tmp):
            writable_tmp = os.environ.get("TMPDIR", "/tmp")

        output_path = os.path.join(writable_tmp, "docker")

        # Set Go build environment variables directly (R33: no shell env in recipe)
        os.environ["GOOS"] = "linux"
        os.environ["GOARCH"] = "arm64"
        os.environ["CGO_ENABLED"] = "1"
        os.environ["GOTOOLCHAIN"] = "local"
        os.environ["DISABLE_WARN_OUTSIDE_CONTAINER"] = "1"
        os.environ["GIT_DISCOVERY_ACROSS_FILESYSTEM"] = "1"
        os.environ["TMPDIR"] = writable_tmp
        os.environ["GOTMPDIR"] = writable_tmp

        ldflags = (
            "-X github.com/docker/cli/cli/version.GitCommit=29.5.3"
            " -X github.com/docker/cli/cli/version.BuildTime=2026-07-16T04:00:00Z"
            " -X github.com/docker/cli/cli/version.Version=29.5.3"
        )
        cmd = (
            f'go build -mod=vendor -o "{output_path}"'
            f" -tags grpcnotrace"
            f' -ldflags "{ldflags}"'
            f" github.com/docker/cli/cmd/docker"
        )
        self.run(cmd, cwd=src)

        # Sign the docker binary at the writable path (trusted for signing)
        sign_elf(output_path)

        # Copy signed binary to build folder
        build_dir = os.path.join(self.build_folder, "build")
        os.makedirs(build_dir, exist_ok=True)
        shutil.copy(output_path, os.path.join(build_dir, "docker"))

    def package(self):
        copy(self, "docker", src=os.path.join(self.build_folder, "build"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
