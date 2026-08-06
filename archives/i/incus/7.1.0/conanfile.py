#!/usr/bin/env python3
"""Conan recipe for incus 7.1.0 — Go-based container manager.

incus is a Go project (not C/C++). This recipe builds client tools and
utilities using the Go compiler. Some binaries require CGO (fuidshift,
incus-benchmark, lxd-to-incus) with platform-specific fixes for OHOS.

Built binaries:
  - incus (client CLI, CGO_ENABLED=0)
  - incus-migrate (CGO_ENABLED=0, -tags netgo)
  - incus-simplestreams (CGO_ENABLED=0)
  - incus-user (CGO_ENABLED=0)
  - incus-agent (CGO_ENABLED=0, -tags agent,netgo)
  - fuidshift (CGO_ENABLED=1, needs libacl + libcap)
  - incus-benchmark (CGO_ENABLED=1)
  - lxd-to-incus (CGO_ENABLED=1)

Excluded (require unavailable C dependencies):
  - incusd (needs cowsql + liblxc + libudev)
  - lxc-to-incus (needs liblxc dev)
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class IncusConan(ConanFile):
    name = "incus"
    version = "7.1.0"
    description = "Powerful system container and virtual machine manager"
    license = "Apache-2.0"
    homepage = "https://github.com/lxc/incus"
    url = ""

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_go(self):
        """Find Go binary in PATH or common locations."""
        go_bin = shutil.which("go")
        if go_bin:
            return go_bin
        # Check Harmonybrew
        brew_go = os.path.expanduser("~/.harmonybrew/bin/go")
        if os.path.isfile(brew_go):
            return brew_go
        raise RuntimeError("Go compiler not found. Install Go (e.g., via Harmonybrew: brew install go)")

    def _find_gnu_ld(self):
        """Find GNU ld for CGO builds (OHOS lld has libxml2 dependency issues)."""
        ld = shutil.which("ld")
        if ld and "harmonybrew" in ld:
            return ld
        brew_ld = os.path.expanduser("~/.harmonybrew/opt/binutils/bin/ld")
        if os.path.isfile(brew_ld):
            return brew_ld
        return None

    def _get_include_paths(self):
        """Get include paths for CGO builds (acl, libcap, gettext)."""
        brew_inc = os.path.expanduser("~/.harmonybrew/include")
        if os.path.isdir(brew_inc):
            return brew_inc
        return None

    def _get_lib_paths(self):
        """Get library paths for CGO builds."""
        brew_lib = os.path.expanduser("~/.harmonybrew/lib")
        if os.path.isdir(brew_lib):
            return brew_lib
        return None

    def build(self):
        apply_conandata_patches(self)
        go_bin = self._find_go()
        gnu_ld = self._find_gnu_ld()
        inc_path = self._get_include_paths()
        lib_path = self._get_lib_paths()

        # Set up Go environment in os.environ (Conan 2.x compatible)
        arch_str = str(self.settings.arch)
        goarch = "arm64" if "arm" in arch_str or "aarch" in arch_str else "amd64"

        os.environ["GOTOOLCHAIN"] = "local"
        os.environ["GOOS"] = "linux"
        os.environ["GOARCH"] = goarch
        os.environ.setdefault("GOPROXY", "https://goproxy.cn,direct")
        os.environ.setdefault("GOPATH", os.path.expanduser("~/go"))

        # Use sandbox tmp dir for Go linker (OHOS HMDFS doesn't support mmap)
        sandbox_tmp = "/data/storage/el2/base/files/tmp"
        if os.path.isdir("/data/storage/el2/base/files"):
            os.environ["TMPDIR"] = sandbox_tmp
            os.environ["GOTMPDIR"] = sandbox_tmp
            os.environ["TMP"] = sandbox_tmp
            os.environ["TEMP"] = sandbox_tmp

        # CGO settings for OHOS platform
        cgo_cflags = "-D__MUSL__ -Wno-macro-redefined"
        if inc_path:
            cgo_cflags += f" -I{inc_path}"
        cgo_ldflags = ""
        if lib_path:
            cgo_ldflags += f" -L{lib_path}"
            cur_ld = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = lib_path + (":" + cur_ld if cur_ld else "")

        go_path = os.environ["GOPATH"]
        bin_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)

        # Build CGO_ENABLED=0 binaries
        os.environ["CGO_ENABLED"] = "0"
        cgo0_targets = [
            ["install", "-v", "./cmd/incus"],
            ["install", "-v", "-tags", "netgo", "./cmd/incus-migrate"],
            ["install", "-v", "./cmd/incus-simplestreams"],
            ["install", "-v", "./cmd/incus-user"],
            ["install", "-v", "-tags", "agent,netgo", "./cmd/incus-agent"],
        ]
        for target in cgo0_targets:
            self.run(f'{go_bin} {" ".join(target)}')

        # Build CGO_ENABLED=1 binaries
        os.environ["CGO_ENABLED"] = "1"
        os.environ.setdefault("CC", "clang")
        os.environ["CGO_CFLAGS"] = cgo_cflags
        os.environ["CGO_LDFLAGS"] = cgo_ldflags

        ldflags = f"-tmpdir {sandbox_tmp}"
        if gnu_ld:
            ldflags += " -linkmode external -extld=clang"

        cgo1_targets = [
            ("./cmd/fuidshift", "fuidshift"),
            ("./cmd/incus-benchmark", "incus-benchmark"),
            ("./cmd/lxd-to-incus", "lxd-to-incus"),
        ]
        for target, bin_name in cgo1_targets:
            output_path = os.path.join(bin_dir, bin_name)
            self.run(f'{go_bin} build -ldflags="{ldflags}" -o "{output_path}" {target}')

        # Copy CGO_ENABLED=0 binaries from GOPATH/bin to build/bin
        gopath_bin = os.path.join(go_path, "bin")
        for bin_name in ["incus", "incus-migrate", "incus-simplestreams", "incus-user", "incus-agent"]:
            src = os.path.join(gopath_bin, bin_name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(bin_dir, bin_name))

    def package(self):
        bin_dir = os.path.join(self.build_folder, "bin")
        if os.path.isdir(bin_dir):
            for f in os.listdir(bin_dir):
                src = os.path.join(bin_dir, f)
                if os.path.isfile(src):
                    self.copy(f, src="bin", dst="bin")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
