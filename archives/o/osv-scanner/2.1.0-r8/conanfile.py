#!/usr/bin/env python3
"""Conan recipe for osv-scanner 2.1.0-r8 — Go project.

osv-scanner is a Go vulnerability scanner tool. This recipe builds two
binaries: osv-scanner and osv-reporter, using the Go toolchain.

Key OHOS adaptations:
- Go toolchain auto-detection (PATH, $HOME/usr/local/go, HNP, /usr/local/go)
- Go internal tools must be signed to execute on OHOS (ELF signature requirement)
- fallocate() returns EACCES on HMDFS/tmpfs; toolexec wrapper redirects
  linker output to /dev/shm which supports fallocate
- Compiled binaries must be signed with binary-sign-tool
- CGO_ENABLED=0 for pure Go compilation (no C dependencies)
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.errors import ConanInvalidConfiguration


# toolexec wrapper script — redirects Go linker output to /dev/shm
# to work around fallocate() EACCES on HMDFS/tmpfs.
# Go linker only handles ENOTSUP/EPERM, not EACCES, so we intercept
# the link tool call and redirect its -o output to /dev/shm, then
# copy the result back to the original path.
_TOOLEXEC_WRAPPER = r"""#!/data/service/hnp/bin/bash
set -eu
TOOL="$1"
shift
IS_LINKER=false
OUTPUT_FILE=""
NEW_ARGS=()
SHM_OUTPUT=""
for arg in "$@"; do
    if [[ "$arg" == -o ]]; then
        IS_LINKER=true
        NEW_ARGS+=("$arg")
        continue
    fi
    if [[ "$IS_LINKER" == true && -z "$OUTPUT_FILE" ]]; then
        OUTPUT_FILE="$arg"
        SHM_OUTPUT="/dev/shm/$(basename "$OUTPUT_FILE").$$"
        NEW_ARGS+=("$SHM_OUTPUT")
    else
        NEW_ARGS+=("$arg")
    fi
done
if [[ "$IS_LINKER" == true && -n "$SHM_OUTPUT" ]]; then
    "$TOOL" "${NEW_ARGS[@]}"
    cp "$SHM_OUTPUT" "$OUTPUT_FILE"
    rm -f "$SHM_OUTPUT"
else
    exec "$TOOL" "$@"
fi
"""


# ── Go toolchain auto-download constants ──
# CI workers don't have Go pre-installed; the recipe downloads it on demand.
GO_VERSION = "1.24.4"
GO_TARBALL = f"go{GO_VERSION}.linux-arm64.tar.gz"
# Google's official Chinese mirror — accessible from CI workers
GO_DOWNLOAD_URL = f"https://golang.google.cn/dl/{GO_TARBALL}"
GO_SHA256 = "d5501ee5aca0f258d5fe9bfaed401958445014495dc115f202d43d5210b45241"


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

        # --- 1. Auto-detect Go toolchain ---
        goroot, go_bin = self._find_go_toolchain()

        # --- 2. Set up Go environment via os.environ ---
        # Conan 2.x self.run() env parameter expects env file names (e.g. "conanbuild"),
        # NOT KEY=VALUE strings. Set environment variables directly via os.environ
        # and use env=None in self.run() to skip env file loading.
        home = os.path.expanduser("~")
        tmpdir = os.environ.get("TMPDIR", os.path.join(home, "tmp"))
        gopath = os.environ.get("GOPATH", os.path.join(home, "go"))
        goproxy = os.environ.get("GOPROXY", "https://goproxy.cn,direct")
        gocache = os.path.join(tmpdir, "go-cache")
        gotmpdir = os.path.join(tmpdir, "go-tmp")

        os.environ["GOROOT"] = goroot
        os.environ["GOPATH"] = gopath
        os.environ["GOPROXY"] = goproxy
        os.environ["TMPDIR"] = tmpdir
        os.environ["GOCACHE"] = gocache
        os.environ["GOTMPDIR"] = gotmpdir
        os.environ["GOOS"] = "linux"
        os.environ["GOARCH"] = "arm64" if str(self.settings.arch) == "armv8" else "amd64"
        os.environ["CGO_ENABLED"] = "0"
        # Prepend Go bin dir to PATH so `go` is findable
        go_bin_dir = os.path.dirname(go_bin)
        current_path = os.environ.get("PATH", "")
        if go_bin_dir not in current_path:
            os.environ["PATH"] = f"{go_bin_dir}:{current_path}"

        # Create required directories
        for d in [gopath, tmpdir, gocache, gotmpdir]:
            os.makedirs(d, exist_ok=True)

        build_dir = self.source_folder

        # --- 3. OHOS-specific: sign Go internal tools + create toolexec wrapper ---
        toolexec_arg = ""
        sign_tool = None
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

            # Sign Go internal tools if not already signed (OHOS ELF signature requirement)
            self._ensure_go_tools_signed(goroot, sign_tool)

            # Create toolexec wrapper if it doesn't exist
            toolexec_script = os.environ.get(
                "TOOLEXEC_WRAPPER",
                os.path.join(tmpdir, "toolexec_wrapper.sh")
            )
            if not os.path.exists(toolexec_script):
                os.makedirs(os.path.dirname(toolexec_script), exist_ok=True)
                with open(toolexec_script, "w") as f:
                    f.write(_TOOLEXEC_WRAPPER)
                os.chmod(toolexec_script, 0o755)
            toolexec_arg = f"-toolexec {toolexec_script}"

        # --- 4. Download dependencies ---
        self.run('go mod download', env=None, cwd=build_dir)

        # --- 5. Build osv-scanner ---
        self.run(f'go build {toolexec_arg} -o osv-scanner ./cmd/osv-scanner/', env=None, cwd=build_dir)

        # --- 6. Build osv-reporter ---
        self.run(f'go build {toolexec_arg} -o osv-reporter ./cmd/osv-reporter/', env=None, cwd=build_dir)

        # --- 7. Sign output binaries on OHOS (ELF signature requirement) ---
        if str(self.settings.os) == "OHOS":
            for binary in ["osv-scanner", "osv-reporter"]:
                signed = f"{binary}-signed"
                self.run(
                    f'{sign_tool} sign -inFile {binary} -outFile {signed} '
                    f'-selfSign 1 -signAlg SHA256withECDSA',
                    env=None, cwd=build_dir
                )
                # Replace unsigned with signed
                os.remove(os.path.join(build_dir, binary))
                shutil.move(
                    os.path.join(build_dir, signed),
                    os.path.join(build_dir, binary)
                )
                os.chmod(os.path.join(build_dir, binary), 0o755)

    def _find_go_toolchain(self):
        """Auto-detect Go toolchain from PATH, common paths, or download it.

        Search order:
        1. go in PATH (shutil.which)
        2. $HOME/usr/local/go/bin/go (user install)
        3. $HNP_PUBLIC_HOME/go/bin/go (HNP-managed Go)
        4. /usr/local/go/bin/go (standard Linux install path)
        5. Download from official mirror (CI workers don't have Go pre-installed)
        """
        # 1. Try PATH
        go_bin = shutil.which("go")
        if go_bin:
            goroot = os.path.dirname(os.path.dirname(go_bin))
            # Verify GOROOT has expected directory structure (pkg/ must exist)
            if os.path.isdir(os.path.join(goroot, "pkg")):
                return goroot, go_bin

        # 2. Try common installation paths
        home = os.path.expanduser("~")
        hnp_home = os.environ.get("HNP_PUBLIC_HOME", "/data/service/hnp")
        candidates = [
            os.path.join(home, "usr", "local", "go", "bin", "go"),
            os.path.join(hnp_home, "go", "bin", "go"),
            "/usr/local/go/bin/go",
        ]
        for candidate in candidates:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                goroot = os.path.dirname(os.path.dirname(candidate))
                # Verify GOROOT has expected directory structure
                if os.path.isdir(os.path.join(goroot, "pkg")):
                    return goroot, candidate

        # 3. Download Go toolchain (CI workers don't have Go pre-installed)
        return self._download_go_toolchain()

    def _download_go_toolchain(self):
        """Download and extract Go toolchain for CI environments.

        CI workers don't have Go pre-installed. This method downloads the
        official Go tarball from Google's mirror, verifies its SHA256,
        and extracts it to a cache directory.
        """
        import hashlib
        import tarfile
        import urllib.request

        # Determine cache directory — prefer DOWNLOAD_CACHE (CI), fallback to TMPDIR
        cache_dir = os.environ.get("DOWNLOAD_CACHE", "")
        if not cache_dir:
            tmpdir = os.environ.get("TMPDIR", os.path.join(os.path.expanduser("~"), "tmp"))
            cache_dir = os.path.join(tmpdir, "go-toolchain")

        goroot = os.path.join(cache_dir, "go")
        go_bin = os.path.join(goroot, "bin", "go")

        # Check if already downloaded and extracted
        if os.path.isfile(go_bin) and os.access(go_bin, os.X_OK):
            self.output.info(f"Using cached Go {GO_VERSION} toolchain at {goroot}")
            return goroot, go_bin

        os.makedirs(cache_dir, exist_ok=True)
        tarball_path = os.path.join(cache_dir, GO_TARBALL)

        # Download if not cached
        if not os.path.isfile(tarball_path):
            self.output.info(f"Downloading Go {GO_VERSION} toolchain from {GO_DOWNLOAD_URL}...")
            try:
                urllib.request.urlretrieve(GO_DOWNLOAD_URL, tarball_path)
            except Exception as e:
                raise ConanInvalidConfiguration(
                    f"Failed to download Go toolchain from {GO_DOWNLOAD_URL}: {e}. "
                    f"Please install Go manually or set GOROOT/GO_BIN_PATH environment variables."
                )

        # Verify SHA256
        sha256_hash = hashlib.sha256()
        with open(tarball_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        actual_sha256 = sha256_hash.hexdigest()
        if actual_sha256 != GO_SHA256:
            os.remove(tarball_path)
            raise ConanInvalidConfiguration(
                f"Go toolchain SHA256 mismatch: expected {GO_SHA256}, got {actual_sha256}. "
                f"The download may be corrupted."
            )

        # Extract
        self.output.info(f"Extracting Go toolchain to {cache_dir}...")
        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(cache_dir)

        if not os.path.isfile(go_bin):
            raise ConanInvalidConfiguration(
                f"Go binary not found after extraction at {go_bin}. "
                f"Please check the tarball contents."
            )

        self.output.info(f"Go {GO_VERSION} toolchain ready at {goroot}")
        return goroot, go_bin

    def _sign_elf_binary(self, binary_path, sign_tool, binary_name=None):
        """Sign an ELF binary with binary-sign-tool if not already signed.

        On OHOS, unsigned ELF binaries cannot be executed. This method
        checks if the binary has a .codesign section and signs it if not.
        """
        if not os.path.isfile(binary_path):
            return
        # Skip if already signed (has .codesign ELF section)
        if self._is_elf_signed(binary_path):
            return
        name = binary_name or os.path.basename(binary_path)
        signed_path = f"{binary_path}-signed"
        try:
            self.run(
                f'{sign_tool} sign -inFile "{binary_path}" -outFile "{signed_path}" '
                f'-selfSign 1 -signAlg SHA256withECDSA',
                env=None
            )
            os.remove(binary_path)
            shutil.move(signed_path, binary_path)
            os.chmod(binary_path, 0o755)
        except Exception as e:
            if os.path.exists(signed_path):
                os.remove(signed_path)
            raise ConanInvalidConfiguration(
                f"Failed to sign Go binary '{name}' at {binary_path}: {e}. "
                f"Unsigned ELF binaries cannot execute on OHOS. "
                f"Check binary-sign-tool availability and permissions."
            )

    def _ensure_go_tools_signed(self, goroot, sign_tool):
        """Ensure Go's binaries are signed for OHOS execution.

        Signs two categories of ELF binaries:
        1. GOROOT/bin/go and GOROOT/bin/gofmt — the main entry points
        2. GOROOT/pkg/tool/linux_arm64/* — internal tools (compile, link, asm, etc.)

        On OHOS, unsigned ELF binaries cannot be executed.
        """
        # 1. Sign main go and gofmt binaries
        for binary_name in ["go", "gofmt"]:
            binary_path = os.path.join(goroot, "bin", binary_name)
            self._sign_elf_binary(binary_path, sign_tool, binary_name)

        # 2. Sign internal tools
        tooldir = os.path.join(goroot, "pkg", "tool", "linux_arm64")
        if not os.path.isdir(tooldir):
            return

        tools = [
            "compile", "link", "asm", "buildid", "cgo", "cover", "fix",
            "nm", "objdump", "pack", "preprofile", "test2json", "trace",
            "addr2line", "covdata", "doc", "pprof", "vet",
        ]
        for tool_name in tools:
            tool_path = os.path.join(tooldir, tool_name)
            self._sign_elf_binary(tool_path, sign_tool, tool_name)

    def _is_elf_signed(self, path):
        """Check if an ELF binary has a .codesign section (OHOS signature)."""
        try:
            readelf = shutil.which("readelf") or "/data/service/hnp/bin/readelf"
            result = subprocess.run(
                [readelf, "-S", path],
                capture_output=True, text=True, timeout=5
            )
            return ".codesign" in result.stdout
        except Exception:
            return False

    def package(self):
        # Copy both binaries to bin/ (binaries are built in source_folder)
        copy(self, "osv-scanner", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "osv-reporter", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Pure Go binary application — no shared libraries
        self.cpp_info.libs = []
        # Add bin/ to bindirs for consumers (Conan 2.x API)
        self.cpp_info.bindirs = ["bin"]
