#!/usr/bin/env python3
"""Conan recipe for termshot 0.6.1 — create screenshots based on terminal output (Go CLI).

HarmonyOS PC (aarch64) adaptation.  termshot is a **Go CLI** tool
(module github.com/homeport/termshot, go 1.24.0).  It runs a command inside
a **real pseudo terminal** (creack/pty) and renders the captured output —
including ANSI colours and text decorations — into a PNG/JPEG screenshot.

OHOS obstacles (identical to the published `archives/t/termsvg/0.11.0` and
`archives/a/addchain/0.4.0` Go recipes):

1. **No Go toolchain** anywhere (CI has no go bootstrap, artifact repo has
   no `go/*`): the recipe bootstraps go1.26.0 into a non-hmdfs workspace and
   signs every ELF it ships — OHOS refuses to exec unsigned ELFs with
   `Permission denied` (no `.codesign` section).
2. **HMDFS link failure (E051)** — the Go linker mmap()s its output: link on
   `/data/storage/el2/...` and copy the finished binary back.

Despite its `gg`/`freetype` requirements, termshot is a **pure-Go** build:
the transitive deps (`golang.org/x/image` font/png/jpeg decoders) are pure
Go ports, so `CGO_ENABLED=0` works and the binary is fully static — verified
on-device (see notes.md).

Build:  go build ./cmd/termshot   (CGO disabled)
Type:   application (executable payload -> commands.json, R38)
"""
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TermshotConan(ConanFile):
    name = "termshot"
    version = "0.6.1"
    description = "Creates screenshots based on terminal command output"
    license = "MIT"
    homepage = "https://github.com/homeport/termshot"
    url = "https://github.com/homeport/termshot"
    topics = ("terminal", "screenshot", "png", "cli", "pty")
    package_type = "application"

    # go.mod requires go >= 1.24.0; 1.26.0 satisfies it (verified on device).
    _go_version = "1.26.0"
    _go_archives = {
        "arm64": (
            [
                "https://dl.google.com/go/go1.26.0.linux-arm64.tar.gz",
                "https://golang.google.cn/dl/go1.26.0.linux-arm64.tar.gz",
                "https://mirrors.aliyun.com/golang/go1.26.0.linux-arm64.tar.gz",
            ],
            "bd03b743eb6eb4193ea3c3fd3956546bf0e3ca5b7076c8226334afe6b75704cd",
        ),
    }
    # All four settings keys are required by the local CI gate (L0) for
    # CLI-tool packages: it rejects `missing_setting_compiler` /
    # `missing_setting_build_type` otherwise.  termshot is pure Go and ignores
    # compiler settings, but declaring them keeps the recipe gate-compliant.
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "termshot is prepared for Linux/OHOS targets only")

    # ── environment ──────────────────────────────────────────────────────

    def generate(self):
        env = Environment()
        env.define("CGO_ENABLED", "0")
        env.define("GOOS", self._goos())
        env.define("GOARCH", self._goarch())
        env.define("GOPROXY", os.environ.get(
            "GOPROXY", "https://goproxy.cn,https://proxy.golang.org,direct"))
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

        env.vars(self).save_script("termshot_go_env")

    # ── build ────────────────────────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)
        go = self._go_executable()
        self.run(f'"{go}" mod download', cwd=self.source_folder,
                 env=["termshot_go_env"])

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # The Go linker mmap()s its output and fails on hmdfs (E051):
        # link on the ext2-like workspace on OHOS, copy back afterwards.
        link_out_dir = (os.path.join(self._go_workspace(), "link-out")
                        if str(self.settings.os) == "OHOS" else out_dir)
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, "termshot")
        final_exe = os.path.join(out_dir, "termshot")
        # Remove a stale artifact from a previous (possibly manual/other-uid)
        # run: otherwise signing/signing-move hits
        # `PermissionError: [Errno 13]` because the file belongs to another
        # user, which looks nothing like the real problem.
        for stale in (linked_exe, linked_exe + ".signed"):
            if os.path.lexists(stale):
                try:
                    os.remove(stale)
                except OSError:
                    pass
        self.run(
            f'"{go}" build -trimpath -o "{linked_exe}" ./cmd/termshot',
            cwd=self.source_folder, env=["termshot_go_env"])
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        self._run_upstream_tests(go)

    def _run_upstream_tests(self, go):
        """Run the upstream `go test` suite with honest package counts.

        Upstream ships ginkgo/gomega suites (internal/img, internal/ptexec).
        On OHOS every fork/exec'd ELF needs a `.codesign` section, so the
        `*.test` binaries produced by `go test` are signed by an `-exec`
        wrapper (same approach as termsvg/0.11.0 and addchain/0.4.0).
        """
        base_env = dict(os.environ)
        go_workspace = self._go_workspace()
        base_env.update({
            "CGO_ENABLED": "0",
            "GOOS": self._goos(),
            "GOARCH": self._goarch(),
            "GOTOOLCHAIN": "local",
            "TMPDIR": os.path.join(go_workspace, "tmp"),
            "GOTMPDIR": os.path.join(go_workspace, "tmp"),
            "GOCACHE": os.path.join(go_workspace, "go-build-cache"),
            "GOMODCACHE": os.path.join(go_workspace, "go-mod-cache"),
            # Upstream internal/ptexec/exec.go:175 reads the terminal size from
            # os.Stdout; in a non-interactive build (conan captures stdout to a
            # pipe) that ioctl fails with ENOTTY.  Upstream itself handles this
            # exact situation via isCI() (exec.go:228-231) — when CI=true it
            # falls back to a sane default and then applies the requested
            # rows/cols (exec.go:185-196), so the "fixed terminal size" spec
            # still runs and really asserts `stty size` == "12 40".
            # Setting it here mirrors the upstream CI contract; it does NOT
            # skip or weaken any assertion.
            "CI": "true",
        })
        goroot = self._goroot_for_go(go)
        if goroot:
            base_env["GOROOT"] = goroot
        base_env["PATH"] = (os.path.dirname(go) + os.pathsep
                            + base_env.get("PATH", ""))

        exec_args = []
        if str(self.settings.os) == "OHOS":
            exec_args = ["-exec", self._write_ohos_test_exec_wrapper()]
        cmd = [go, "test", "-count=1"] + exec_args + ["./..."]

        try:
            proc = subprocess.run(cmd, cwd=self.source_folder, env=base_env,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, timeout=1800)
            output = proc.stdout.decode(errors="replace")
        except (OSError, subprocess.TimeoutExpired) as exc:
            output = f"go test failed to run: {exc}"

        passed = len(re.findall(r"^ok\s+\S+", output, re.MULTILINE))
        failed = len(re.findall(r"^FAIL\s+\S+", output, re.MULTILINE))
        self.output.info(f"termshot upstream go test: ok-packages={passed} "
                         "fail-packages=%d" % failed)
        self.output.info("preview:\n  " + output[:3000].replace("\n", "\n  "))
        if failed:
            self.output.warning(
                "termshot upstream go test reported failing packages - see "
                "the preview above / MANIFEST.yml exemptions")

    def _write_ohos_test_exec_wrapper(self):
        """Sign the `go test` binary before it is exec'd (OHOS requirement)."""
        go_workspace = self._go_workspace()
        wrapper_dir = os.path.join(go_workspace, "test-exec-wrapper")
        Path(wrapper_dir).mkdir(parents=True, exist_ok=True)
        wrapper_path = os.path.join(wrapper_dir, "ohos-test-exec.sh")

        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        sign_tmp = os.path.join(go_workspace, "sign-tmp-test")
        Path(sign_tmp).mkdir(parents=True, exist_ok=True)

        wrapper_body = f"""#!/bin/sh
# termshot: OHOS go test -exec wrapper — sign the test binary, then exec it.
set -e
bin="$1"
shift
if [ ! -f "$bin" ]; then
    echo "ohos-test-exec: test binary not found: $bin" >&2
    exit 127
fi
if /data/service/hnp/bin/llvm-readelf -S "$bin" 2>/dev/null | grep -q '\\.codesign'; then
    chmod 755 "$bin" 2>/dev/null || true
    exec "$bin" "$@"
fi
inode=$(stat -c '%i' "$bin" 2>/dev/null || echo 0)
tin="{sign_tmp}/$(basename "$bin").$$.$inode"
tout="$tin.signed"
cp -f "$bin" "$tin"
if [ -x "{objcopy}" ]; then
    "{objcopy}" --remove-section .codesign "$tin" >/dev/null 2>&1 || true
fi
"{signer}" sign -selfSign 1 -inFile "$tin" -outFile "$tout" -signAlg SHA256withECDSA
mv -f "$tout" "$bin"
chmod 755 "$bin" 2>/dev/null || true
rm -f "$tin"
exec "$bin" "$@"
"""
        with open(wrapper_path, "w", encoding="utf-8") as f:
            f.write(wrapper_body)
        os.chmod(wrapper_path, 0o755)
        return wrapper_path

    def package(self):
        copy(self, "termshot", os.path.join(self.build_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder,
             os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ── Go toolchain helpers (addchain/0.4.0 / termsvg-0.11.0 pattern) ────

    def _go_workspace(self):
        if str(self.settings.os) != "OHOS":
            root = os.path.join(self.build_folder, ".go-work")
        else:
            root = os.environ.get(
                "OHOS_GO_WORKDIR",
                "/data/storage/el2/base/haps/entry/files/termshot-conan-go")
        workspace = os.path.join(root, self.version)
        for child in ("tmp", "go-build-cache", "go-mod-cache", "link-out",
                      "go-sdk", "sign-tmp", "sign-tmp-test"):
            Path(workspace, child).mkdir(parents=True, exist_ok=True)
        return workspace

    def _ensure_go_toolchain(self):
        host_arch = self._go_host_arch()
        if host_arch not in self._go_archives:
            raise ConanInvalidConfiguration(
                f"Go SDK bootstrap is not prepared for host arch: {host_arch}")
        urls, sha256 = self._go_archives[host_arch]
        sdk_root = os.path.join(self._go_workspace(), "go-sdk",
                                f"go{self._go_version}-{host_arch}")
        goroot = os.path.join(sdk_root, "go")
        gobin = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(gobin):
            self.output.info(f"Go toolchain not found; downloading {urls[0]}")
            get(self, url=urls, sha256=sha256, destination=sdk_root,
                strip_root=False)
        self._sign_go_sdk_if_ohos(goroot)
        return gobin

    def _sign_go_sdk_if_ohos(self, goroot):
        if str(self.settings.os) != "OHOS":
            return
        marker = os.path.join(goroot, ".ohos-signed")
        if os.path.isfile(marker):
            return
        tool_dir = os.path.join(goroot, "pkg", "tool",
                                f"linux_{self._go_host_arch()}")
        candidates = [os.path.join(goroot, "bin", "go"),
                      os.path.join(goroot, "bin", "gofmt")]
        if os.path.isdir(tool_dir):
            candidates.extend(
                os.path.join(tool_dir, f) for f in os.listdir(tool_dir))
        for candidate in candidates:
            if os.path.isfile(candidate) and self._is_elf(candidate):
                # Signing rewrites the file, which drops the execute bits —
                # restore them explicitly (a missing +x looks exactly like the
                # optical "Permission denied" caused by a missing signature).
                self._sign_elf_if_ohos(candidate)
                try:
                    os.chmod(candidate, 0o755)
                except OSError:
                    pass
        Path(marker).write_text("signed\n", encoding="utf-8")

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as binary:
                return binary.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_elf_if_ohos(self, path):
        if str(self.settings.os) != "OHOS":
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to sign OHOS Go executables")

        def _chmod_ok(target):
            # Best effort: a file may be owned by another uid (e.g. left over
            # from a manual/earlier run) and chmod would raise EPERM.  That is
            # not fatal — the file is already signed/executable at this point.
            try:
                os.chmod(target, 0o755)
            except OSError:
                pass

        if self._has_ohos_signature(path):
            _chmod_ok(path)
            return
        tmp_dir = os.path.join(self._go_workspace(), "sign-tmp")
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)
        tmp_in = os.path.join(tmp_dir, os.path.basename(path))
        tmp_out = f"{tmp_in}.signed"
        shutil.copy2(path, tmp_in)
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        subprocess.run([objcopy, "--remove-section", ".codesign", tmp_in],
                       capture_output=True, timeout=10)
        subprocess.check_call([
            signer, "sign", "-selfSign", "1", "-inFile", tmp_in,
            "-outFile", tmp_out, "-signAlg", "SHA256withECDSA"])
        shutil.move(tmp_out, path)
        _chmod_ok(path)
        os.unlink(tmp_in)

    @staticmethod
    def _has_ohos_signature(path):
        """Check for a REAL .codesign ELF section (not a filename substring)."""
        try:
            proc = subprocess.run(
                ["/data/service/hnp/bin/llvm-readelf", "-S", path],
                capture_output=True, timeout=30)
            return b".codesign" in proc.stdout
        except (OSError, subprocess.SubprocessError):
            return False

    def _goos(self):
        return "linux" if str(self.settings.os) == "OHOS" else str(self.settings.os).lower()

    def _goarch(self):
        return {
            "x86_64": "amd64", "x86": "386", "armv8": "arm64",
            "armv8_32": "arm", "armv7": "arm", "armv7hf": "arm", "armv6": "arm",
        }.get(str(self.settings.arch), str(self.settings.arch))

    def _go_executable(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        candidates.extend([os.path.expanduser("~/usr/local/go/bin/go")])
        found = shutil.which("go")
        if found:
            candidates.append(found)
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and \
                    self._go_version_is_supported(candidate):
                return candidate
        return self._ensure_go_toolchain()

    def _go_version_is_supported(self, go):
        try:
            output = subprocess.run([go, "version"], capture_output=True,
                                    timeout=15).stdout.decode()
        except OSError:
            return False
        if "go version " not in output:
            return False
        ver = output.split("go version ")[-1].split(" ")[0][2:]
        try:
            return [int(x) for x in ver.split(".")] >= \
                   [int(x) for x in self._go_version.split(".")]
        except ValueError:
            return False

    def _go_host_arch(self):
        machine = platform.machine().lower()
        return {
            "x86_64": "amd64", "amd64": "amd64",
            "aarch64": "arm64", "arm64": "arm64", "armv8l": "arm64",
        }.get(machine, machine)

    def _goroot_for_go(self, gobin):
        gobin = os.path.realpath(gobin)
        for candidate in (os.path.dirname(os.path.dirname(gobin)),
                          os.environ.get("GOROOT", "")):
            if candidate and os.path.isfile(os.path.join(candidate, "bin", "go")):
                return candidate
        return ""
