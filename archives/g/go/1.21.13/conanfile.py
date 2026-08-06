#!/usr/bin/env python3
"""Conan recipe for Go 1.21.13 toolchain on HarmonyOS.

Go uses a self-bootstrapping build system (make.bash), not Autotools/CMake.
This recipe downloads the Go source and a pre-built Go bootstrap binary,
strips/signs the bootstrap for HarmonyOS ELF compatibility, then builds
the Go toolchain with ELF signing integrated via patches.
"""
import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy

HNP_BIN = "/data/service/hnp/bin"
SIGN_TOOL = f"{HNP_BIN}/binary-sign-tool"
OBJCOPY = f"{HNP_BIN}/llvm-objcopy"
STRIP = f"{HNP_BIN}/strip"
BASH = f"{HNP_BIN}/bash"

# Go 1.24.3 bootstrap binary (linux-arm64) — pre-built from go.dev
GO_BOOTSTRAP_URL = "https://go.dev/dl/go1.24.3.linux-arm64.tar.gz"
GO_BOOTSTRAP_SHA256 = "a463cb59382bd7ae7d8f4c68846e73c4d589f223c589ac76871b66811ded7836"


def is_elf(filepath):
    try:
        with open(filepath, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except Exception:
        return False


def sign_elf(path):
    """Strip and sign a single ELF file for HarmonyOS."""
    if not os.path.isfile(path) or not is_elf(path):
        return
    # Strip to fix non-standard ELF (Go SHT_STRTAB not null-terminated)
    subprocess.run([STRIP, path], capture_output=True, timeout=30)
    # Remove existing codesign section
    subprocess.run([OBJCOPY, "--remove-section", ".codesign", path],
                   capture_output=True, timeout=10)
    # Sign
    tmp = path + ".signed.tmp"
    for attempt in range(3):
        r = subprocess.run(
            [SIGN_TOOL, "sign", "-inFile", path, "-outFile", tmp, "-selfSign", "1"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0 and os.path.exists(tmp):
            shutil.move(tmp, path)
            break
        import time; time.sleep(1)
    else:
        tmp_path = Path(tmp)
        if tmp_path.exists():
            tmp_path.unlink()
    os.chmod(path, 0o755)


def sign_dir(directory):
    """Recursively sign all ELF files in a directory."""
    for root, dirs, files in os.walk(directory):
        for f in files:
            sign_elf(os.path.join(root, f))


class GoConan(ConanFile):
    name = "go"
    version = "1.21.13"
    description = "Go programming language compiler and toolchain"
    license = "BSD-3-Clause"
    homepage = "https://go.dev"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        # Try downloading from go.dev; fall back to local copy if network fails
        src_data = self.conan_data["sources"]
        try:
            get(self, **src_data, strip_root=True)
        except Exception as e:
            self.output.warning(f"Download from {src_data.get('url')} failed: {e}")
            # Check common local paths for pre-downloaded source
            local_paths = [
                os.path.expanduser("~/tmp/builds/go-1.21.13.tar.gz"),
                "/storage/Users/currentUser/tmp/builds/go-1.21.13.tar.gz",
            ]
            found = None
            for p in local_paths:
                if os.path.isfile(p):
                    found = p
                    break
            if not found:
                raise e
            self.output.info(f"Using local copy: {found}")
            # Extract with root stripping
            import tarfile, tempfile, shutil
            tmpdir = tempfile.mkdtemp(
                dir=os.environ.get("TMPDIR", "/data/storage/el2/base/cache"))
            try:
                with tarfile.open(found, "r:gz") as tar:
                    tar.extractall(path=tmpdir)
                # The tarball has 'go/' as top-level — move its contents
                go_root = os.path.join(tmpdir, "go")
                if os.path.isdir(go_root):
                    for item in os.listdir(go_root):
                        src = os.path.join(go_root, item)
                        dst = os.path.join(self.source_folder, item)
                        shutil.move(src, dst)
                else:
                    for item in os.listdir(tmpdir):
                        src = os.path.join(tmpdir, item)
                        dst = os.path.join(self.source_folder, item)
                        shutil.move(src, dst)
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)

    def build(self):
        # Apply ELF signing patches to make.bash and cmd/dist/build.go
        apply_conandata_patches(self)

        src_dir = self.source_folder
        src_go = os.path.join(src_dir, "src")

        # 1. Download and prepare the Go bootstrap binary
        bootstrap_dir = os.path.join(src_dir, "go-bootstrap")
        try:
            get(self, url=GO_BOOTSTRAP_URL, sha256=GO_BOOTSTRAP_SHA256,
                filename="go-bootstrap.tar.gz", strip_root=True,
                destination=bootstrap_dir)
        except Exception as e:
            self.output.warning(f"Bootstrap download failed: {e}")
            # Check common local paths for pre-downloaded bootstrap
            local_paths = [
                os.path.expanduser("~/tmp/go-bootstrap/go1.24.3.linux-arm64.tar.gz"),
                "/storage/Users/currentUser/tmp/go-bootstrap/go1.24.3.linux-arm64.tar.gz",
            ]
            found = None
            for p in local_paths:
                if os.path.isfile(p):
                    found = p
                    break
            if not found:
                raise e
            self.output.info(f"Using local bootstrap copy: {found}")
            import tarfile
            with tarfile.open(found, "r:gz") as tar:
                tar.extractall(path=bootstrap_dir)
            # Bootstrap extracted to bootstrap_dir/go/ — adjust GOROOT_BOOTSTRAP
            bootstrap_dir = os.path.join(bootstrap_dir, "go")

        # 2. Strip and sign the bootstrap Go binaries
        sign_dir(bootstrap_dir)

        # 3. Build on HMFS — Go linker mmap fails on tmpfs
        # Copy source to HMFS filesystem for building
        hmfs_base = "/data/storage/el2/base/cache/go-conan-build"
        hmfs_src = os.path.join(hmfs_base, "go-1.21.13")
        if os.path.exists(hmfs_src):
            shutil.rmtree(hmfs_src)
        shutil.copytree(src_dir, hmfs_src, symlinks=True, ignore_dangling_symlinks=True)
        # Copy bootstrap to HMFS as well
        hmfs_bootstrap = os.path.join(hmfs_base, "go-bootstrap")
        if os.path.exists(hmfs_bootstrap):
            shutil.rmtree(hmfs_bootstrap)
        shutil.copytree(bootstrap_dir, hmfs_bootstrap, symlinks=True, ignore_dangling_symlinks=True)

        hmfs_tmp = os.path.join(hmfs_base, "tmp")
        os.makedirs(hmfs_tmp, exist_ok=True)
        gocache = os.path.join(hmfs_tmp, "go-cache")
        os.makedirs(gocache, exist_ok=True)

        # 4. Run make.bash (patches handle ELF signing during build)
        # Use subprocess directly for full env control
        env = os.environ.copy()
        env["GOROOT_BOOTSTRAP"] = hmfs_bootstrap
        env["GOROOT"] = hmfs_src
        env["CGO_ENABLED"] = "0"
        env["TMPDIR"] = hmfs_tmp
        env["GOTMPDIR"] = hmfs_tmp
        env["GOCACHE"] = gocache
        env["GOOS"] = "linux"
        env["GOARCH"] = "arm64"

        hmfs_src_go = os.path.join(hmfs_src, "src")
        # Use bash -c with cd to avoid HMDFS getcwd issues
        result = subprocess.run(
            [BASH, "-c", f"cd '{hmfs_src_go}' && ./make.bash"],
            env=env,
            timeout=1800,
        )
        if result.returncode != 0:
            raise Exception(f"make.bash failed with exit code {result.returncode}")

        # 5. Copy built Go tree back to Conan build folder
        # Copy everything except go-bootstrap and patches
        for item in os.listdir(hmfs_src):
            if item == "go-bootstrap":
                continue
            src_path = os.path.join(hmfs_src, item)
            dst_path = os.path.join(src_dir, item)
            if os.path.exists(dst_path):
                shutil.rmtree(dst_path) if os.path.isdir(dst_path) else os.remove(dst_path)
            shutil.copytree(src_path, dst_path, symlinks=True) if os.path.isdir(src_path) else shutil.copy2(src_path, dst_path)

    def package(self):
        src_dir = self.source_folder
        # Copy the entire Go tree to the package directory
        # Exclude go-bootstrap (build tool) and patches
        copy(self, "*", src_dir, self.package_folder,
             excludes=["go-bootstrap*", "patches*", ".git*"])

    def package_info(self):
        bin_dir = "bin"
        self.cpp_info.bindirs = [bin_dir]
        # GOROOT environment variable for downstream consumers
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Set GOROOT for downstream packages that need the Go toolchain
        self.buildenv_info.define("GOROOT", self.package_folder)
        self.buildenv_info.prepend_path("PATH", bin_dir)
