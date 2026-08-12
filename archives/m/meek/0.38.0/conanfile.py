#!/usr/bin/env python3
"""Conan 2.x recipe — meek 0.38.0 (Tor pluggable transport)

Build system: Go (go build)
License: CC0-1.0
Homepage: https://www.torproject.org

meek is a blocking-resistant pluggable transport for Tor. It encodes data
streams as HTTPS requests/responses and relays them through third-party
servers. This recipe builds both meek-client and meek-server binaries.

R26: Go binaries are statically linked by default (CGO_ENABLED=0).
R33: GOOS/GOARCH derived from Conan settings, not hardcoded shell vars.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get, export_conandata_patches
from conan.tools.layout import basic_layout


class MeekConan(ConanFile):
    name = "meek"
    version = "0.38.0"
    description = "Blocking-resistant pluggable transport for Tor"
    license = "CC0-1.0"
    homepage = "https://www.torproject.org"
    url = "https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/meek"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def requirements(self):
        # Go modules manage their own dependencies via go.mod (not Conan)
        pass

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # G1完整性: conandata.yml 声明的源/补丁需此方法显式导出
        export_conandata_patches(self)

    def source(self):
        # The official source (gitlab.torproject.org) is unreachable from both
        # the dev machine and CI workers, and the host is not covered by the
        # CI mirror fallback. conandata.yml therefore lists the reachable
        # goproxy.cn module zip first and a file:// fallback to the same zip
        # pre-cached under the shared HOME; Conan get() tries each URL in
        # order until one succeeds (all entries share the same sha256).
        get(self, **self.conan_data["sources"], strip_root=True)
        # Go module zips nest the source under "<module>@<version>/" (a
        # multi-level top dir), so strip_root leaves the tree nested; flatten
        # it so go.mod sits at the source root for `go build ./meek-client`.
        nested = None
        for root, _, files in os.walk(self.source_folder):
            if "go.mod" in files:
                nested = root
                break
        if nested and nested != self.source_folder:
            for entry in os.listdir(nested):
                shutil.move(os.path.join(nested, entry), self.source_folder)
            # Remove the emptied "<module>@<version>" chain (best effort):
            # deepest first, then its (now empty) ancestors.
            dirs = [nested]
            parent = os.path.dirname(nested)
            while parent and parent.startswith(self.source_folder) and parent != self.source_folder:
                dirs.append(parent)
                parent = os.path.dirname(parent)
            for d in dirs:
                try:
                    os.rmdir(d)
                except OSError:
                    pass

    def _goarch(self):
        """Map Conan arch to Go GOARCH (R33: derived from Conan settings)."""
        arch_map = {
            "armv8": "arm64",
            "aarch64": "arm64",
            "x86_64": "amd64",
            "x86": "386",
        }
        goarch = arch_map.get(str(self.settings.arch))
        if goarch is None:
            raise ConanInvalidConfiguration(
                f"Unsupported arch: {self.settings.arch}. "
                f"Supported: {list(arch_map.keys())}"
            )
        return goarch

    def build(self):
        # Go cross-compilation settings (R33: derived from Conan settings)
        # CGO_ENABLED=0: pure Go, static binary (R26)
        # GOOS=linux: HarmonyOS uses Linux kernel (Go has no "ohos" GOOS)
        os.environ["CGO_ENABLED"] = "0"
        os.environ["GOOS"] = "linux"
        os.environ["GOARCH"] = self._goarch()
        os.environ["GOFLAGS"] = "-mod=mod"
        # CI Workers can't reach proxy.golang.org (Go's default GOPROXY); use the
        # reachable goproxy.cn mirror for Go module downloads. setdefault lets an
        # explicit GOPROXY env override this if needed.
        os.environ.setdefault("GOPROXY", "https://goproxy.cn,direct")
        # Conan sandbox strips PATH, so harmonybrew's Go toolchain is unreachable.
        # Inject ~/.harmonybrew/bin into PATH so `go build` finds the `go` binary.
        go_bin = os.path.expanduser("~/.harmonybrew/bin")
        os.environ["PATH"] = go_bin + ":" + os.environ.get("PATH", "")

        # Build meek-client (cwd=source_folder: go.mod lives in source dir)
        self.run('go build -trimpath -ldflags "-s -w" -o meek-client ./meek-client',
                 cwd=self.source_folder)

        # Build meek-server
        self.run('go build -trimpath -ldflags "-s -w" -o meek-server ./meek-server',
                 cwd=self.source_folder)

    def package(self):
        # Binaries are built into source_folder (cwd of go build)
        copy(self, "meek-client", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "meek-server", self.source_folder,
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Terminal tool: no linkable libraries
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
