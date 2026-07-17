#!/usr/bin/env python3
"""Conan recipe for gofumpt — Go CLI tool (formatting).

gofumpt is a Go CLI tool, not a C/C++ library.
Uses custom Go build (CGO_ENABLED=0 static).

CI environment must have Go available in PATH (Go 1.25+).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class GofumptConan(ConanFile):
    name = "gofumpt"
    version = "0.10.0-r0"
    description = "A stricter gofmt, written in Go"
    license = "MIT"
    homepage = "https://github.com/mvdan/gofumpt"
    url = "https://github.com/mvdan/gofumpt"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.output.info("Building gofumpt with Go...")
        # Use /data/storage/el2/base/cache (hmfs) to avoid HMDFS mmap restrictions
        self.run("CGO_ENABLED=0 GOOS=linux GOARCH=arm64 "
                 "GOPROXY=https://goproxy.cn,direct "
                 "TMPDIR=/data/storage/el2/base/cache "
                 "go build -ldflags='-s -w' -o /data/storage/el2/base/cache/gofumpt .")
        # Run upstream tests
        self.output.info("Running upstream tests...")
        self.run("go test ./...")
        # Copy binary from temp cache to build folder
        src_bin = "/data/storage/el2/base/cache/gofumpt"
        dst_bin = os.path.join(self.build_folder, "gofumpt")
        shutil.copy2(src_bin, dst_bin)
        if not os.path.isfile(dst_bin):
            raise RuntimeError(f"Failed to copy gofumpt binary to {dst_bin}")

    def _sign_elf_binary(self, path):
        """Sign ELF binary on OHOS for execution on HarmonyOS.

        Go ELF output has non-standard SHT_STRTAB that must be stripped
        before ELF signing can succeed.
        """
        import subprocess
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        is_ohos = self.settings.os == "OHOS"
        if not os.path.isfile(path):
            self.output.warn(f"Binary not found for signing: {path}")
            return
        try:
            # Step 1: Remove old .codesign section (may not exist)
            r_obj = subprocess.run(
                [objcopy, "--remove-section", ".codesign", path],
                capture_output=True, timeout=10)
            if r_obj.returncode != 0:
                self.output.warn(f"objcopy failed for {os.path.basename(path)} (rc={r_obj.returncode}), skipping signing")
                if is_ohos:
                    raise RuntimeError(f"objcopy failed on HarmonyOS, ELF signing is required: {os.path.basename(path)}")
                return
            # Step 2: Sign with binary-sign-tool
            tmp = path + ".signed.tmp"
            r = subprocess.run(
                [sign_tool, "sign", "-inFile", path, "-outFile", tmp, "-selfSign", "1"],
                capture_output=True, timeout=30)
            if r.returncode == 0 and os.path.exists(tmp):
                os.replace(tmp, path)
                os.chmod(path, 0o755)
                self.output.info(f"ELF signed: {os.path.basename(path)}")
            else:
                msg = f"ELF signing failed for {os.path.basename(path)} (rc={r.returncode})"
                if is_ohos:
                    raise RuntimeError(msg)
                self.output.warn(msg)
        except subprocess.TimeoutExpired:
            msg = f"ELF signing timed out for {os.path.basename(path)}"
            if is_ohos:
                raise RuntimeError(msg)
            self.output.warn(msg)
        except (FileNotFoundError, PermissionError) as e:
            msg = f"ELF signing tool error for {os.path.basename(path)}: {e}"
            if is_ohos:
                raise RuntimeError(msg)
            self.output.warn(msg)

    def package(self):
        copy(self, "gofumpt", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        # Verify binary exists in package
        pkg_bin = os.path.join(self.package_folder, "bin", "gofumpt")
        if not os.path.isfile(pkg_bin):
            raise RuntimeError(f"gofumpt binary not found in package: {pkg_bin}")
        # Sign ELF binary on OHOS (required for execution on HarmonyOS)
        self._sign_elf_binary(pkg_bin)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []