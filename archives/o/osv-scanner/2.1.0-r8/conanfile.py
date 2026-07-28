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
        """Auto-detect Go toolchain from PATH or common installation paths.

        Search order:
        1. go in PATH (shutil.which)
        2. $HOME/usr/local/go/bin/go (user install — most common on OHOS CI workers)
        3. $HNP_PUBLIC_HOME/go/bin/go (HNP-managed Go)
        4. /usr/local/go/bin/go (standard Linux install path)
        """
        # 1. Try PATH
        go_bin = shutil.which("go")
        if go_bin:
            goroot = os.path.dirname(os.path.dirname(go_bin))
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
                return goroot, candidate

        raise ConanInvalidConfiguration(
            "Go toolchain not found. Searched: PATH, $HOME/usr/local/go, "
            "$HNP_PUBLIC_HOME/go, /usr/local/go. "
            "Please install Go or set GOROOT/GO_BIN_PATH environment variables."
        )

    def _ensure_go_tools_signed(self, goroot, sign_tool):
        """Ensure Go's internal tools are signed for OHOS execution.

        Go's internal tools (compile, link, asm, etc.) are ELF binaries
        located in GOROOT/pkg/tool/linux_arm64/. On OHOS, unsigned ELF
        binaries cannot be executed. This method signs any unsigned tools.
        """
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
            if not os.path.isfile(tool_path):
                continue
            # Skip if already signed (has .codesign ELF section)
            if self._is_elf_signed(tool_path):
                continue
            # Sign the tool
            signed_path = f"{tool_path}-signed"
            try:
                self.run(
                    f'{sign_tool} sign -inFile "{tool_path}" -outFile "{signed_path}" '
                    f'-selfSign 1 -signAlg SHA256withECDSA',
                    env=None
                )
                os.remove(tool_path)
                shutil.move(signed_path, tool_path)
                os.chmod(tool_path, 0o755)
            except Exception:
                # Signing may fail if already signed or tool not needed
                if os.path.exists(signed_path):
                    os.remove(signed_path)

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
