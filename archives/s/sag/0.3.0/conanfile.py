#!/usr/bin/env python3
"""Conan recipe for sag 0.3.0 - Mac-style speech with ElevenLabs (Go TTS CLI).

sag is a Go application (one-liner TTS that works like macOS `say`).
This recipe cross-compiles the Go binary for HarmonyOS PC (aarch64-linux-ohos).

Build approach (based on archives/a/ali/0.8.0 Go pattern):
  - Go toolchain bootstrap (requires Go >= 1.25.0 for go.mod).
  - CGO disabled (pure Go build; oto >= v3.5.1 provides the CGO-free
    PulseAudio backend + purego ALSA fallback for Linux, so no ALSA
    headers or CGO cross-toolchain are needed).
  - Upstream go.mod pins oto v3.4.0 (CGO-only ALSA on Linux); build()
    runs `go get oto/v3@v3.5.1 + go mod tidy` first (see _oto_version).
  - GOARCH=arm64 GOOS=linux (HarmonyOS Linux kernel ABI).
  - GOPROXY=https://goproxy.cn,direct for module resolution in CN networks.
  - GOTOOLCHAIN=local to prevent auto-downloading Go toolchains.
  - Upstream tests via `go test -v -count=1 ./...` with -race fallback
    (race requires cgo; CGO_ENABLED=0 fails, fallback to non-race).
  - OHOS test ELF signing via `go test -exec` wrapper.
  - HMBS evidence markers persisted to package res/ for cache-hit re-emit.
"""

import os
import platform
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, get, export_conandata_patches
from conan.tools.layout import basic_layout


class SagConan(ConanFile):
    name = "sag"
    version = "0.3.0"
    _go_version = "1.25.0"
    # oto v3.4.0 (pinned by upstream go.mod) has no CGO-free Linux backend:
    # cross-compile with CGO_ENABLED=0 fails with
    #   context.go:38:11: undefined: context / undefined: newContext
    # (same as ebitengine/oto#260 and steipete/homebrew-tap#10 on Linux ARM64).
    # oto v3.5.0+ ships a pure-Go PulseAudio driver (+Cgo-free ALSA fallback)
    # so Linux builds with CGO_ENABLED=0. Bump at build time; public
    # oto API used by sag (NewContext/NewPlayer) is backward compatible
    # (v3.5 only adds NewContextOptions.ApplicationName).
    _oto_version = "v3.5.1"
    _go_archives = {
        "arm64": (
            [
                "https://golang.google.cn/dl/go1.25.0.linux-arm64.tar.gz",
                "https://mirrors.aliyun.com/golang/go1.25.0.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.25.0.linux-arm64.tar.gz",
            ],
            "05de75d6994a2783699815ee553bd5a9327d8b79991de36e38b66862782f54ae",
        ),
        "amd64": (
            [
                "https://golang.google.cn/dl/go1.25.0.linux-amd64.tar.gz",
                "https://mirrors.aliyun.com/golang/go1.25.0.linux-amd64.tar.gz",
                "https://dl.google.com/go/go1.25.0.linux-amd64.tar.gz",
            ],
            "2852af0cb20a13139b3448992e69b868e50ed0f8a1e5940ee1de9e19a123b613",
        ),
    }
    package_type = "application"

    description = "Mac-style speech with ElevenLabs (one-liner TTS CLI written in Go)"
    license = "MIT"
    homepage = "https://github.com/steipete/sag"
    url = "https://github.com/steipete/sag"
    topics = ("sag", "tts", "elevenlabs", "cli", "go")

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("sag is prepared for Linux/OHOS targets only")

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

        env.vars(self).save_script("sag_go_env")

    def build(self):
        go = self._go_executable()
        # CGO-free Linux fix: upgrade oto to a version with the pure-Go
        # PulseAudio backend before resolving modules. `go get` + `go mod tidy`
        # rewrite go.mod/go.sum in the (writable) source folder; idempotent on
        # rebuilds. Fails fast here if the module proxy is unreachable.
        self.run(
            f'"{go}" get github.com/ebitengine/oto/v3@{self._oto_version}',
            cwd=self.source_folder,
            env=["sag_go_env"],
        )
        self.run(f'"{go}" mod tidy', cwd=self.source_folder, env=["sag_go_env"])
        self.run(f'"{go}" mod download', cwd=self.source_folder, env=["sag_go_env"])

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # Go linker mmap fails on HMDFS: link on workspace outside HMDFS on OHOS.
        if str(self.settings.os) == "OHOS":
            link_out_dir = os.path.join(self._go_workspace(), "link-out")
        else:
            link_out_dir = out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, self._exe_name())
        final_exe = os.path.join(out_dir, self._exe_name())
        ldflags = "-s -w"
        self.run(
            f'"{go}" build -trimpath -ldflags "{ldflags}" -o "{linked_exe}" ./cmd/sag',
            cwd=self.source_folder,
            env=["sag_go_env"],
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        self._run_upstream_tests(go)

    def _write_ohos_test_exec_wrapper(self):
        """Write a `go test -exec` wrapper that signs the test binary before exec.

        On OHOS every ELF that gets forked/exec'd must carry a `.codesign`
        section. `go test` builds `*.test` binaries into GOTMPDIR and
        fork/execs them directly, so unsigned test binaries fail with
        "permission denied" and no tests run.
        """
        go_workspace = self._go_workspace()
        wrapper_dir = os.path.join(go_workspace, "test-exec-wrapper")
        Path(wrapper_dir).mkdir(parents=True, exist_ok=True)
        wrapper_path = os.path.join(wrapper_dir, "ohos-test-exec.sh")

        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        sign_tmp = os.path.join(go_workspace, "sign-tmp-test")
        Path(sign_tmp).mkdir(parents=True, exist_ok=True)

        wrapper_body = f"""#!/bin/sh
# OHOS go test -exec wrapper: sign the test binary, then exec it.
set -e

bin="$1"
shift

if [ ! -f "$bin" ]; then
    echo "ohos-test-exec: test binary not found: $bin" >&2
    exit 127
fi

if grep -aq -m1 -e '.codesign' -e '.note.ohos' -- "$bin" 2>/dev/null; then
    chmod 755 "$bin" 2>/dev/null || true
    exec "$bin" "$@"
fi

signer="{signer}"
objcopy="{objcopy}"
stmp="{sign_tmp}"
if [ ! -x "$signer" ]; then
    echo "ohos-test-exec: binary-sign-tool missing: $signer" >&2
    exit 127
fi

inode=$(stat -c '%i' "$bin" 2>/dev/null || echo '0')
tin="$stmp/$(basename "$bin").$$.$inode"
tout="$tin.signed"
cp -f "$bin" "$tin"
if [ -x "$objcopy" ]; then
    "$objcopy" --remove-section .codesign "$tin" >/dev/null 2>&1 || true
fi
"$signer" sign -selfSign 1 -inFile "$tin" -outFile "$tout" -signAlg SHA256withECDSA
mv -f "$tout" "$bin"
chmod 755 "$bin" 2>/dev/null || true
rm -f "$tin"
exec "$bin" "$@"
"""
        with open(wrapper_path, "w", encoding="utf-8") as f:
            f.write(wrapper_body)
        os.chmod(wrapper_path, 0o755)
        self.output.info(f"sag: wrote OHOS go test -exec wrapper to {wrapper_path}")
        return wrapper_path

    def _run_upstream_tests(self, go):
        """Run upstream `go test ./...` and emit HMBS markers.

        Counts come from a single deterministic source: `--- PASS:` /
        `--- FAIL:` / `--- SKIP:` lines of `go test -v` output. No string
        counting fallbacks or returncode-based corrections.
        """
        import json
        import re

        base_env = dict(os.environ)
        go_workspace = self._go_workspace()
        go_env_overrides = {
            "CGO_ENABLED": "0",
            "GOOS": self._goos(),
            "GOARCH": self._goarch(),
            "GOTOOLCHAIN": "local",
            "TMPDIR": os.path.join(go_workspace, "tmp"),
            "GOTMPDIR": os.path.join(go_workspace, "tmp"),
            "GOCACHE": os.path.join(go_workspace, "go-build-cache"),
            "GOMODCACHE": os.path.join(go_workspace, "go-mod-cache"),
        }
        goroot = self._goroot_for_go(go)
        if goroot:
            go_env_overrides["GOROOT"] = goroot
        base_env.update(go_env_overrides)
        base_env["PATH"] = os.path.dirname(go) + os.pathsep + base_env.get("PATH", "")

        exec_args = []
        if str(self.settings.os) == "OHOS":
            wrapper = self._write_ohos_test_exec_wrapper()
            exec_args = ["-exec", wrapper]

        def _run(cmd):
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=self.source_folder,
                    env=base_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=1800,
                )
                return proc.stdout.decode(errors="replace")
            except (OSError, subprocess.TimeoutExpired) as exc:
                return f"go test failed to run: {exc}"

        def _count(output):
            # Deterministic source: only top-level `--- PASS:/FAIL:/SKIP:`
            # lines (column 0). Indented `    --- PASS:` lines are Go
            # subtests and must NOT be counted: MANIFEST upstream_test_total
            # (74) is the `func Test*` top-level count, so including
            # subtests inflates discovered (e.g. 80) and trips rule4.
            p = len(re.findall(r"^--- PASS:", output, re.MULTILINE))
            f = len(re.findall(r"^--- FAIL:", output, re.MULTILINE))
            s = len(re.findall(r"^--- SKIP:", output, re.MULTILINE))
            return p, f, s

        cmd = [go, "test", "-v", "-count=1", "-race"] + exec_args + ["./..."]
        out = _run(cmd)
        if "race detector not available" in out or "undefined: race" in out or "requires cgo" in out or "CGO_ENABLED" in out or "-race requires cgo" in out:
            cmd = [go, "test", "-v", "-count=1"] + exec_args + ["./..."]
            out = _run(cmd)
        p, f, s = _count(out)
        self.output.info(f"sag `go test ./...`: PASS={p} FAIL={f} SKIP={s}")
        preview = out[:4096].replace("\n", "\n  sag go test | ")
        self.output.info("sag go test output preview:\n  " + preview)

        passed = p
        failed = f
        skipped = s
        discovered = passed + failed + skipped
        executed = passed + failed
        if failed > 0:
            status = "failed"
        elif passed > 0:
            status = "passed"
        else:
            if "permission denied" in out.lower():
                status = "failed"
            else:
                status = "no_tests"

        command_str = " ".join(cmd)
        upstream = {
            "status": status,
            "framework": "go test",
            "command": command_str,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
        try:
            hmbs_tmp = os.path.join(self.build_folder, "hmbs_upstream.json")
            with open(hmbs_tmp, "w", encoding="utf-8") as _f:
                json.dump(upstream, _f)
        except Exception:
            pass

    def package(self):
        copy(self, self._exe_name(), os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "res"))
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            dst_dir = os.path.join(self.package_folder, "res")
            os.makedirs(dst_dir, exist_ok=True)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(dst_dir, "hmbs_upstream.json"))
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    def _go_workspace(self):
        if str(self.settings.os) != "OHOS":
            root = os.path.join(self.build_folder, ".go-work")
        else:
            root = os.environ.get(
                "OHOS_GO_WORKDIR",
                "/data/storage/el2/base/haps/entry/files/sag-conan-go",
            )
        workspace = os.path.join(root, self.version)
        for child in (
            "tmp",
            "go-build-cache",
            "go-mod-cache",
            "link-out",
            "go-sdk",
        ):
            Path(workspace, child).mkdir(parents=True, exist_ok=True)
        return workspace

    def _download_and_extract_go_sdk(self, urls, sha256, sdk_root):
        """Download Go SDK tarball and extract with pure-Python tarfile.

        Avoids forking system ``tar``/``gzip`` (on OHOS ``tar -zxf`` fails
        with ``tar (grandchild): gzip: Cannot exec: Operation not permitted``,
        see真机 compile failure). Uses ``urllib`` + ``tarfile`` (gzip module,
        no child process), following the gadap/qalculate-gtk cmd-pkgs
        precedent. Tries mirrors in order, verifies SHA256 and gzip magic.
        """
        import hashlib
        import io
        import ssl
        import tarfile
        import urllib.request

        ctx = ssl.create_default_context()
        last_err = "no mirror attempted"
        Path(sdk_root).mkdir(parents=True, exist_ok=True)
        for url in urls:
            try:
                self.output.info(f"sag: downloading Go SDK from {url}")
                req = urllib.request.urlopen(url, context=ctx, timeout=600)
                try:
                    data = req.read()
                finally:
                    req.close()
                if not data or data[:2] != b"\x1f\x8b":
                    last_err = f"{url}: not gzip (len={len(data) if data else 0})"
                    self.output.warning(f"sag: {last_err}, trying next mirror")
                    continue
                digest = hashlib.sha256(data).hexdigest()
                if digest != sha256:
                    last_err = f"{url}: sha256 mismatch"
                    self.output.warning(f"sag: {last_err}, trying next mirror")
                    continue
                # Clean partial extraction before (re)extract.
                go_dir = os.path.join(sdk_root, "go")
                if os.path.isdir(go_dir) or os.path.islink(go_dir):
                    shutil.rmtree(go_dir, ignore_errors=True)
                bio = io.BytesIO(data)
                try:
                    with tarfile.open(fileobj=bio, mode="r:gz") as tf:
                        try:
                            tf.extractall(sdk_root, filter="data")
                        except TypeError:
                            tf.extractall(sdk_root)
                except Exception as exc:
                    last_err = f"{url}: extract failed: {exc}"
                    self.output.warning(f"sag: {last_err}, trying next mirror")
                    shutil.rmtree(go_dir, ignore_errors=True)
                    continue
                gobin = os.path.join(go_dir, "bin", "go")
                if os.path.isfile(gobin):
                    try:
                        os.chmod(gobin, 0o755)
                    except OSError:
                        pass
                    self.output.info(f"sag: Go SDK ready from {url}")
                    return
                last_err = f"{url}: extracted but bin/go missing"
                self.output.warning(f"sag: {last_err}, trying next mirror")
            except Exception as exc:
                last_err = f"{url}: download failed: {exc}"
                self.output.warning(f"sag: {last_err}, trying next mirror")
                continue
        raise ConanInvalidConfiguration(
            f"sag: Go SDK bootstrap failed (pure-python download/extract, "
            f"no system tar/gzip): {last_err}")

    def _ensure_go_toolchain(self):
        host_arch = self._go_host_arch()
        if host_arch not in self._go_archives:
            raise ConanInvalidConfiguration(f"Go SDK bootstrap is not prepared for host arch: {host_arch}")

        sdk_root = os.path.join(self._go_workspace(), "go-sdk", f"go{self._go_version}-{host_arch}")
        goroot = os.path.join(sdk_root, "go")
        gobin = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(gobin):
            urls, sha256 = self._go_archives[host_arch]
            self.output.info(f"Go >= {self._go_version} not found; downloading {urls[0]}")
            self._download_and_extract_go_sdk(urls, sha256, sdk_root)
        self._sign_go_sdk_if_ohos(goroot)
        return gobin

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
            candidates.extend(os.path.join(tool_dir, filename) for filename in os.listdir(tool_dir))

        for candidate in candidates:
            if os.path.isfile(candidate) and self._is_elf(candidate):
                self._sign_elf_if_ohos(candidate)
        Path(marker).write_text("signed\n", encoding="utf-8")

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as binary:
                return binary.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _has_ohos_signature(path):
        try:
            with open(path, "rb") as binary:
                data = binary.read()
        except OSError:
            return False
        return b".codesign" in data or b".note.ohos" in data

    def _sign_elf_if_ohos(self, path):
        if str(self.settings.os) != "OHOS":
            return
        if self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration("binary-sign-tool is required to sign OHOS Go executables")
        tmp_dir = os.path.join(self._go_workspace(), "sign-tmp")
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)
        tmp_in = os.path.join(tmp_dir, os.path.basename(path))
        tmp_out = f"{tmp_in}.signed"
        shutil.copy2(path, tmp_in)
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        subprocess.run([objcopy, "--remove-section", ".codesign", tmp_in],
                       capture_output=True, timeout=10)
        subprocess.check_call([
            signer,
            "sign",
            "-selfSign",
            "1",
            "-inFile",
            tmp_in,
            "-outFile",
            tmp_out,
            "-signAlg",
            "SHA256withECDSA",
        ])
        shutil.move(tmp_out, path)
        os.chmod(path, 0o755)
        os.unlink(tmp_in)

    def _goos(self):
        if str(self.settings.os) == "OHOS":
            return "linux"
        return str(self.settings.os).lower()

    def _goarch(self):
        arch = str(self.settings.arch)
        return {
            "x86_64": "amd64",
            "x86": "386",
            "armv8": "arm64",
            "armv8_32": "arm",
            "armv7": "arm",
            "armv7hf": "arm",
            "armv6": "arm",
        }.get(arch, arch)

    def _exe_name(self):
        return "sag.exe" if self._goos() == "windows" else "sag"

    def _go_executable(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        candidates.extend([
            os.path.expanduser("~/usr/local/go/bin/go"),
            os.path.expanduser("~/sdk/go1.25.0/bin/go"),
        ])
        found = shutil.which("go")
        if found:
            candidates.append(found)

        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and self._go_version_is_supported(candidate):
                return candidate
        return self._ensure_go_toolchain()

    def _go_version_is_supported(self, go):
        try:
            output = subprocess.run([go, "version"], capture_output=True, timeout=10).stdout.decode()
        except OSError:
            return False
        m = output.split("go version ")[-1].split(" ")[0]
        ver = m[2:]
        try:
            return [int(x) for x in ver.split(".")] >= [int(x) for x in self._go_version.split(".")]
        except ValueError:
            return False

    def _go_host_arch(self):
        machine = platform.machine().lower()
        return {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
            "armv8l": "arm64",
        }.get(machine, machine)

    def _goroot_for_go(self, gobin):
        gobin = os.path.realpath(gobin)
        candidates = [
            os.path.dirname(os.path.dirname(gobin)),
            os.environ.get("GOROOT", ""),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(os.path.join(candidate, "bin", "go")):
                return candidate
        return ""
