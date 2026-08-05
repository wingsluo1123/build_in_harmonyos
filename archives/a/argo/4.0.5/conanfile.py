#!/usr/bin/env python3
"""Conan recipe for argo 4.0.5 — Argo Workflows CLI (Go).

Argo Workflows is a Kubernetes-native workflow engine. The `argo` CLI is
built from the `./cmd/argo` entry point with CGO_ENABLED=0 (pure static Go
binary). The build requires:

  - Go >= 1.25.7 (argo v4.0.5 go.mod constraint)
  - UI placeholder (ui/dist/app/index.html) for go:embed in server package
  - HMDFS-safe workspace for Go linker mmap (ext2 partition on OHOS)
  - ELF signing on OHOS (unsigned binaries cannot execute)

Build command:
    CGO_ENABLED=0 go build -trimpath -ldflags "-s -w \
      -X ...version=v4.0.5 -extldflags -static" -o argo ./cmd/argo
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ArgoConan(ConanFile):
    name = "argo"
    version = "4.0.5"

    # Go SDK bootstrap — downloaded if no usable Go is on PATH/GOROOT.
    _go_version = "1.26.3"
    _go_archives = {
        "amd64": (
            [
                "https://golang.google.cn/dl/go1.26.3.linux-amd64.tar.gz",
                "https://dl.google.com/go/go1.26.3.linux-amd64.tar.gz",
            ],
            "2b2cfc7148493da5e73981bffbf3353af381d5f93e789c82c79aff64962eb556",
        ),
        "arm64": (
            [
                "https://golang.google.cn/dl/go1.26.3.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.26.3.linux-arm64.tar.gz",
            ],
            "9d89a3ea57d141c2b22d70083f2c8459ba3890f2d9e818e7e933b75614936565",
        ),
    }

    package_type = "application"

    description = "Argo Workflows CLI — Kubernetes-native workflow engine command-line tool"
    license = "Apache-2.0"
    homepage = "https://argoproj.github.io/argo-workflows/"
    url = "https://github.com/argoproj/argo-workflows"
    topics = ("kubernetes", "workflow", "cli", "go", "devops")

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("argo is prepared for Linux/OHOS targets only")

    def generate(self):
        env = Environment()
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", self._goos())
        env.define("GOARCH", self._goarch())
        env.define("GOPROXY", os.environ.get("GOPROXY", "https://goproxy.cn,https://proxy.golang.org,direct"))
        env.define("GOSUMDB", os.environ.get("GOSUMDB", "sum.golang.google.cn"))
        env.define("GOTOOLCHAIN", "local")

        go_workspace = self._go_workspace()
        env.define("TMPDIR", os.path.join(go_workspace, "tmp"))
        env.define("GOTMPDIR", os.path.join(go_workspace, "tmp"))
        env.define("GOCACHE", os.path.join(go_workspace, "go-build-cache"))
        env.define("GOMODCACHE", os.path.join(go_workspace, "go-mod-cache"))

        gobin = self._go_executable()
        goroot = self._goroot_for_go(gobin)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(gobin))

        env.vars(self).save_script("argo_go_env")

    def build(self):
        apply_conandata_patches(self)

        # Create UI placeholder for go:embed (ui/embed.go: //go:embed dist/app)
        ui_dist = os.path.join(self.source_folder, "ui", "dist", "app")
        os.makedirs(ui_dist, exist_ok=True)
        index_html = os.path.join(ui_dist, "index.html")
        if not os.path.isfile(index_html):
            Path(index_html).write_text(
                "<!DOCTYPE html><html><head><title>Argo UI</title></head>"
                "<body><p>Argo UI placeholder</p></body></html>\n",
                encoding="utf-8",
            )

        go = self._go_executable()
        self._check_go_version(go)
        self.run(f'"{go}" mod download', cwd=self.source_folder, env=["argo_go_env"])

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # OHOS: write link output to tmpfs workspace, then copy to bin/ after signing
        link_out_dir = os.path.join(self._go_workspace(), "link-out") if str(self.settings.os) == "OHOS" else out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, self._exe_name())
        final_exe = os.path.join(out_dir, self._exe_name())

        ldflags = (
            "-s -w"
            " -X github.com/argoproj/argo-workflows/v4.version=v4.0.5"
            " -X github.com/argoproj/argo-workflows/v4.buildDate=2026-06-01T00:00:00Z"
            " -X github.com/argoproj/argo-workflows/v4.gitCommit=0ab1452144d8f4d57c50b37ce50dad218868e950"
            " -X github.com/argoproj/argo-workflows/v4.gitTreeState=clean"
            " -extldflags -static"
        )
        self.run(
            f'"{go}" build -trimpath -ldflags "{ldflags}" -o "{linked_exe}" ./cmd/argo',
            cwd=self.source_folder,
            env=["argo_go_env"],
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

    def package(self):
        copy(self, self._exe_name(), os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ---------- Go toolchain helpers (adapted from wego 2.4 / chkbit 6.6.0) ----------

    def _go_workspace(self):
        base = os.environ.get("OHC_GO_WORKSPACE")
        if base:
            ws = os.path.join(base, f"argo-{self.version}")
        elif str(self.settings.os) == "OHOS":
            ws = os.path.join("/data/storage/el2/base/haps/entry/files", f"argo-{self.version}-build")
        else:
            ws = os.path.join(self.build_folder, "go-workspace")
        for sub in ("", "tmp", "go-build-cache", "go-mod-cache", "link-out"):
            os.makedirs(os.path.join(ws, sub), exist_ok=True)
        return ws

    def _ensure_go_toolchain(self):
        arch = self._go_host_arch()
        if arch not in self._go_archives:
            raise ConanInvalidConfiguration(f"Go SDK bootstrap is not prepared for host arch: {arch}")
        urls, expected_sha = self._go_archives[arch]
        sdk_dir = os.path.join(os.path.expanduser("~"), ".goenv", "versions", self._go_version)
        go_bin = os.path.join(sdk_dir, "bin", "go")
        if not os.path.isfile(go_bin):
            os.makedirs(sdk_dir, exist_ok=True)
            archive_path = os.path.join(sdk_dir, "go.tar.gz")
            downloaded = False
            for url in urls:
                try:
                    self.run(f'curl -fsSL -o "{archive_path}" "{url}"', env=[])
                    downloaded = True
                    break
                except Exception:
                    continue
            if not downloaded:
                raise ConanInvalidConfiguration(f"Failed to download Go {self._go_version} SDK for {arch}")
            actual_sha = self._sha256(archive_path)
            if actual_sha != expected_sha:
                raise ConanInvalidConfiguration(f"Go SDK SHA256 mismatch: {actual_sha} != {expected_sha}")
            self.run(f'tar -xzf "{archive_path}" -C "{sdk_dir}" --strip-components=1', env=[])
            os.remove(archive_path)
        self._sign_go_sdk_if_ohos(sdk_dir)
        return go_bin

    def _sign_go_sdk_if_ohos(self, goroot):
        if str(self.settings.os) != "OHOS":
            return
        marker = os.path.join(goroot, ".ohos-signed")
        if os.path.isfile(marker):
            return
        tool_dir = os.path.join(goroot, "pkg", "tool", f"linux_{self._go_host_arch()}")
        candidates = [
            os.path.join(goroot, "bin", "go"),
            os.path.join(goroot, "bin", "gofmt"),
        ]
        if os.path.isdir(tool_dir):
            candidates.extend(os.path.join(tool_dir, fn) for fn in os.listdir(tool_dir))
        for candidate in candidates:
            if os.path.isfile(candidate) and self._is_elf(candidate):
                self._sign_elf_if_ohos(candidate)
        Path(marker).write_text("signed\n", encoding="utf-8")

    def _sign_elf_if_ohos(self, path):
        if str(self.settings.os) != "OHOS":
            return
        if self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return
        sign_tool = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(sign_tool):
            raise ConanInvalidConfiguration(f"binary-sign-tool not found: {sign_tool}")
        if not self._is_elf(path):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.isfile(objcopy):
            subprocess.run([objcopy, "--remove-section", ".codesign", path], capture_output=True, timeout=10)
        tmp = path + ".signed.tmp"
        for attempt in range(3):
            r = subprocess.run(
                [sign_tool, "sign", "-inFile", path, "-outFile", tmp, "-selfSign", "1"],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0 and os.path.isfile(tmp):
                shutil.move(tmp, path)
                os.chmod(path, 0o755)
                return
        raise ConanInvalidConfiguration(f"ELF signing failed for {path}")

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except Exception:
            return False

    @staticmethod
    def _has_ohos_signature(path):
        try:
            r = subprocess.run(
                ["/data/service/hnp/bin/llvm-readelf", "-S", path],
                capture_output=True, text=True, timeout=10,
            )
            return ".codesign" in r.stdout
        except Exception:
            return False

    def _goos(self):
        return "linux"  # OHOS pre-adaptation: GOOS=linux, GOARCH=arm64

    def _goarch(self):
        arch = str(self.settings.arch)
        if arch in ("x86_64", "amd64"):
            return "amd64"
        if arch in ("armv8", "aarch64", "arm64"):
            return "arm64"
        return arch

    def _exe_name(self):
        return "argo.exe" if str(self.settings.os) == "Windows" else "argo"

    def _go_executable(self):
        candidates = [
            os.environ.get("GO"),
            os.environ.get("GOROOT_TMP"),
            shutil.which("go"),
        ]
        for c in candidates:
            if c and os.path.isfile(c) and self._go_version_is_supported(c):
                return c
        return self._ensure_go_toolchain()

    def _go_version_is_supported(self, go):
        try:
            return self._go_version_tuple(go) >= (1, 25, 7)
        except Exception:
            return False

    def _check_go_version(self, go):
        if not self._go_version_is_supported(go):
            raise ConanInvalidConfiguration(f"Go toolchain at {go} is older than 1.25.7")

    @staticmethod
    def _go_version_tuple(go, output=None):
        if output is None:
            r = subprocess.run([go, "version"], capture_output=True, text=True, timeout=10)
            output = r.stdout
        m = re.search(r"go(\d+)\.(\d+)\.(\d+)", output)
        if not m:
            raise ValueError(f"cannot parse go version: {output!r}")
        return tuple(int(x) for x in m.groups())

    @staticmethod
    def _goroot_for_go(go):
        go_path = Path(go).resolve()
        goroot = go_path.parent.parent
        if go_path.parent.name == "bin" and (goroot / "pkg").is_dir():
            return str(goroot)
        return None

    @staticmethod
    def _go_host_arch():
        import platform
        m = platform.machine()
        if m in ("x86_64", "amd64"):
            return "amd64"
        if m in ("aarch64", "arm64"):
            return "arm64"
        return m

    @staticmethod
    def _sha256(path):
        import hashlib
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
