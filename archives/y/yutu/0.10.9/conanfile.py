#!/usr/bin/env python3
"""Conan recipe for yutu 0.10.9 — YouTube CLI / MCP server / AI agent (pure Go)
adapted for OpenHarmony PC (aarch64).

yutu is a pure-Go command-line application: module ``github.com/eat-pray-ai/yutu``
with ``main.go`` at the repository root, so the build is a bare ``go build .``.

Upstream build contract (reproduced from ``.goreleaser.yaml``):

    CGO_ENABLED=0 GO111MODULE=on go build -trimpath -tags=netgo \
        -ldflags "-s -w -X github.com/eat-pray-ai/yutu/cmd.Version=... \
                  -X .../cmd.Commit=... -X .../cmd.CommitDate=... \
                  -X .../cmd.Os=... -X .../cmd.Arch=... -X .../cmd.Builder=..." .

There are no C/C++ library dependencies at all: ``CGO_ENABLED=0`` plus
``-tags=netgo`` selects the pure-Go DNS/TLS stacks, so nothing links against
libc / OpenSSL / libcurl. The upstream ``Dockerfile`` builds ``FROM scratch``
and only copies ``/etc/ssl/certs/ca-certificates.crt`` next to the static
binary, which confirms the binary is fully static.

HarmonyOS notes
---------------
1. No Go toolchain ships with the OHOS image. Per knowledge entry E250
   (``rec_approach: download-go-sdk``, ``rec_impl: inline-build-method``) the Go
   SDK is downloaded inside ``build()`` from authoritative mirrors and never
   declared as a Conan ``requires()``. This matches the 57 existing Go recipes
   in this repository (e.g. ``aiac/5.3.0``, ``abbtr/1.0.4``).
2. The Go linker fails on HMDFS with
   ``mapping output file failed: permission denied`` (knowledge E051/E046).
   Link output is therefore written to an ext2-like writable workspace
   (``/data/storage/el2/base/haps/entry/files``) when targeting OHOS.
3. Every ELF that OHOS will ``fork``/``exec`` must carry a ``.codesign``
   section. Both the produced ``yutu`` binary and the Go SDK tool binaries are
   self-signed with ``binary-sign-tool``.
4. Go module dependencies are resolved through ``GOPROXY`` at build time; no
   module is mirrored into this repository.

Recipe evidence: archives/y/yutu/0.10.9/{manifest.yaml,notes.md}
"""
import json
import os
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class YutuConan(ConanFile):
    name = "yutu"
    version = "0.10.9"

    # go.mod declares `go 1.26.0`; 1.26.5 is the Go SDK used by the existing
    # Go recipes in this repository and satisfies that floor.
    _go_version = "1.26.5"
    _go_archives = {
        "arm64": (
            [
                "https://golang.google.cn/dl/go1.26.5.linux-arm64.tar.gz",
                "https://mirrors.aliyun.com/golang/go1.26.5.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.26.5.linux-arm64.tar.gz",
            ],
            "fe4789e92b1f33358680864bbe8704289e7bb5fc207d80623c308935bd696d49",
        ),
        "amd64": (
            [
                "https://golang.google.cn/dl/go1.26.5.linux-amd64.tar.gz",
                "https://mirrors.aliyun.com/golang/go1.26.5.linux-amd64.tar.gz",
                "https://dl.google.com/go/go1.26.5.linux-amd64.tar.gz",
            ],
            "5c2c3b16caefa1d968a94c1daca04a7ca301a496d9b086e17ad77bb81393f053",
        ),
    }

    # ldflags payload, taken from the v0.10.9 tag (commit 99b3443, 2026-06-21)
    # exactly as .goreleaser.yaml injects it.
    _version = "v0.10.9"
    _commit = "99b3443"
    _commit_date = "2026-06-21T10:38:47Z"
    _builder = "OpenHarmonyPCDeveloper"

    package_type = "application"
    description = "yutu — AI-powered YouTube CLI, MCP server and agent (pure Go)"
    license = "Apache-2.0"
    homepage = "https://github.com/eat-pray-ai/yutu"
    url = "https://github.com/eat-pray-ai/yutu"
    topics = ("youtube", "cli", "mcp", "ai-agent", "go", "ohos")

    settings = "os", "compiler", "build_type", "arch"

    # Worker 侧资源耗尽（fork/内存）的输出特征，非配方缺陷——重试可吸收瞬时压力。
    # 仓内先例：libcom_err/1.47.4、tinyarray/1.2.5、wchartype/0.1 的 CI 失败均
    # 被判定为 worker "resource temporarily unavailable (exit 127)"，非配方问题。
    _INFRA_MARKERS = (
        "resource temporarily unavailable",
        "cannot allocate memory",
        "out of memory",
        "fork failed",
        "cannot fork",
        "unable to fork",
    )

    # 网络类输出特征（CI worker 出网受限）——退避重试可吸收瞬时抖动。
    # 对齐 SKILL v12.18 H2「conan 网络特征重试（reset/timeout/SSL/5xx/DNS）」口径。
    _NETWORK_MARKERS = (
        "i/o timeout",
        "dial tcp",
        "connection timed out",
        "connection reset",
        "connection refused",
        "tls handshake timeout",
        "no such host",
        "temporary failure in name resolution",
        "502 bad gateway",
        "503 service unavailable",
        "context deadline exceeded",
    )

    # Go 模块代理 / 校验和库 —— 单一事实源，generate() 与 _go_env_dict() 必须共用。
    #
    # CI #92484：worker 出网受限，`proxy.golang.org` 与 `dl.google.com` 均连接超时，
    # 而 `mirrors.aliyun.com` 可达（同一轮里 Go SDK 下载回退到 aliyun 后成功）。
    #
    # 分隔符必须用 `|` 而不是 `,`：Go 语义下 `,` 只在前一个代理返回 404/410 时才回退，
    # 遇到连接超时会直接让整条命令失败；`|` 才在任一错误时回退到下一个代理。
    _goproxy = os.environ.get(
        "GOPROXY",
        "https://mirrors.aliyun.com/goproxy/|https://goproxy.cn"
        "|https://proxy.golang.org|direct",
    )
    _gosumdb = os.environ.get("GOSUMDB", "sum.golang.google.cn")

    def export_sources(self):
        # yutu 0.10.9 needs no patches; kept for conandata patch export parity.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("yutu supports Linux and OHOS targets only")

    def _go_env_overrides(self):
        """Single source of truth for the Go build/test environment (R33).

        ``generate()`` (conan env script) and ``_go_env_dict()`` (direct
        ``subprocess`` calls) MUST share this mapping. CI #92484 failed exactly
        because GOPROXY/GOSUMDB were defined only inside ``generate()`` while
        ``go mod download`` had been moved onto a direct ``subprocess`` path:
        Go then silently used its built-in default ``https://proxy.golang.org``,
        which this worker cannot reach (dial tcp timeout), and the build died on
        the first module. Keeping one mapping makes that class of divergence
        impossible.
        """
        go_workspace = self._go_workspace()
        return {
            "CGO_ENABLED": "0",
            "GOOS": self._goos(),
            "GOARCH": self._goarch(),
            "GO111MODULE": "on",
            "GOPROXY": self._goproxy,
            "GOSUMDB": self._gosumdb,
            # Never let the toolchain try to download a different Go release.
            "GOTOOLCHAIN": "local",
            # CI #91930: with the default parallelism `go build` fans out one
            # compiler process per package (each of them multi-threaded), which
            # exhausted the CI worker's process/thread slots — every
            # `compile`/`asm` fork came back with EAGAIN "resource temporarily
            # unavailable". Pin the Go runtime to a single thread so the whole
            # toolchain tree stays within a small budget (inherited by every
            # child compiler).
            "GOMAXPROCS": "1",
            "TMPDIR": os.path.join(go_workspace, "tmp"),
            "GOTMPDIR": os.path.join(go_workspace, "tmp"),
            "GOCACHE": os.path.join(go_workspace, "go-build-cache"),
            "GOMODCACHE": os.path.join(go_workspace, "go-mod-cache"),
        }

    def generate(self):
        env = Environment()
        for key, value in self._go_env_overrides().items():
            env.define(key, value)

        go_workspace = self._go_workspace()
        # Pre-create every path component: the Go toolchain refuses to bootstrap
        # if any of them is missing.
        for subdir in ("tmp", "go-build-cache", "go-mod-cache"):
            os.makedirs(os.path.join(go_workspace, subdir), exist_ok=True)

        gobin = self._go_executable()
        goroot = self._goroot_for_go(gobin)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(gobin))

        # Surface the effective proxy/sumdb in the conan log — CI #92484 was a
        # silent fall-back to Go's built-in GOPROXY and cost a whole CI round.
        self.output.info(f"Go module proxy (GOPROXY): {self._goproxy}")
        self.output.info(f"Go checksum DB (GOSUMDB): {self._gosumdb}")

        env.vars(self).save_script("yutu_go_env")

    def build(self):
        # yutu 0.10.9 ships with `patches: {}` (a pure-Go static build needs no
        # source changes); the call keeps the recipe patch-capable so a future
        # patch only has to be declared in conandata.yml.
        apply_conandata_patches(self)

        go = self._go_executable()
        # Safety net in case generate() was skipped or the workspace moved.
        for subdir in ("tmp", "go-build-cache", "go-mod-cache"):
            os.makedirs(os.path.join(self._go_workspace(), subdir), exist_ok=True)

        self._run_go(go, ["mod", "download"], "go mod download", timeout=3600)

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # The Go linker mmaps its output file; on HMDFS this fails with
        # "mapping output file failed: permission denied" (E051/E046), so on
        # OHOS the link step writes into an ext2-like workspace instead.
        link_out_dir = (
            os.path.join(self._go_workspace(), "link-out")
            if str(self.settings.os) == "OHOS"
            else out_dir
        )
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, "yutu")
        final_exe = os.path.join(out_dir, "yutu")

        # `-p 1` serialises package compilation: one compiler process at a time
        # keeps a CI worker well inside its process/thread budget (CI #91930).
        self._run_go(
            go,
            ["build", "-trimpath", "-p", "1", "-tags", "netgo",
             "-ldflags", self._ldflags(), "-o", linked_exe, "."],
            "go build",
            timeout=7200,
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        # Upstream test evidence (HMBS_UPSTREAM_TEST_RESULT) is published by
        # test_package/conanfile.py; this run keeps the raw go test log inside
        # the conan create output for audit.
        self._run_upstream_tests(go)

    def package(self):
        copy(self, "yutu", os.path.join(self.build_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        # Carry the build-phase upstream test evidence so that test_package can
        # republish the very same numbers on its stdout (HMBS evidence gate).
        copy(self, "upstream-test-result.json", self.build_folder,
             os.path.join(self.package_folder, "share", "yutu"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ── ldflags ──────────────────────────────────────────────────────────────

    def _ldflags(self):
        mod = "github.com/eat-pray-ai/yutu/cmd"
        return " ".join([
            "-s", "-w",
            f"-X {mod}.Version={self._version}",
            f"-X {mod}.Commit={self._commit}",
            f"-X {mod}.CommitDate={self._commit_date}",
            f"-X {mod}.Os={self._goos()}",
            f"-X {mod}.Arch={self._goarch()}",
            f"-X {mod}.Builder={self._builder}",
        ])

    # ── Go command runner (worker-pressure tolerant) ─────────────────────────

    def _run_go(self, go, args, label, timeout=3600, retries=3):
        """Run a Go command, absorbing transient worker resource pressure.

        CI #91930 failed because a parallel ``go build`` exhausted the worker's
        process/thread slots: every ``compile``/``asm`` fork returned EAGAIN
        ("resource temporarily unavailable"). The build is now serialised
        (``-p 1`` + ``GOMAXPROCS=1``); a bounded retry absorbs whatever transient
        pressure remains instead of burning a whole CI run. Non-resource
        failures are reported at once with the real command output.
        """
        env = self._go_env_dict(go)
        argv = [go] + list(args)
        log_path = os.path.join(
            self.build_folder, f"{re.sub(r'[^A-Za-z0-9_.-]+', '_', label)}.log")

        for attempt in range(1, retries + 1):
            try:
                proc = subprocess.run(argv, cwd=self.source_folder, env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      timeout=timeout)
                output = proc.stdout.decode(errors="replace")
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                output = f"{label}: timed out after {timeout}s"
                rc = -1
            except OSError as exc:
                output = f"{label}: could not start: {exc}"
                rc = -1

            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write(output)

            if rc == 0:
                self.output.info(f"{label}: ok (log: {log_path})")
                return output

            infra = any(marker in output.lower() for marker in self._INFRA_MARKERS)
            network = any(marker in output.lower() for marker in self._NETWORK_MARKERS)
            retryable = infra or network
            reason = "worker resource pressure" if infra else ("network" if network else "")
            tail = output[-3000:] if len(output) > 3000 else output
            self.output.warning(
                f"{label}: attempt {attempt}/{retries} failed (rc={rc}"
                f"{', ' + reason if reason else ''})\n{tail}")
            if not retryable or attempt == retries:
                raise ConanException(
                    f"{label} failed (rc={rc}); log: {log_path}; last output:\n{tail}")
            time.sleep(30 * attempt)
        return ""

    # ── upstream tests (R51 evidence trail) ──────────────────────────────────

    def _go_env_dict(self, go):
        """Explicit Go environment; never relies on bare shell variables (R33)."""
        env = dict(os.environ)
        env.update(self._go_env_overrides())
        goroot = self._goroot_for_go(go)
        if goroot:
            env["GOROOT"] = goroot
        env["PATH"] = os.path.dirname(go) + os.pathsep + env.get("PATH", "")
        return env

    def _test_packages(self, go, env):
        """Enumerate the packages that actually carry upstream test files."""
        proc = subprocess.run(
            [go, "list", "-f", "{{.ImportPath}}|{{len .TestGoFiles}}|{{len .XTestGoFiles}}", "./..."],
            cwd=self.source_folder, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900,
        )
        packages = []
        for line in proc.stdout.decode(errors="replace").splitlines():
            parts = line.strip().split("|")
            if len(parts) != 3:
                continue
            try:
                if int(parts[1]) + int(parts[2]) > 0:
                    packages.append(parts[0])
            except ValueError:
                continue
        return packages

    def _run_upstream_tests(self, go):
        """Execute the upstream Go suite on the OHOS target.

        A bare ``go test ./...`` cannot be used here: it links a test binary and
        immediately ``execve``s it, and OHOS refuses to execute an ELF that has
        no ``.codesign`` section (knowledge E128). Every test package is instead
        compiled with ``go test -c``, signed with ``binary-sign-tool`` and then
        executed on its own — the same strategy as ``kor/0.6.8``.
        """
        env = self._go_env_dict(go)
        test_dir = os.path.join(self._go_workspace(), "upstream-tests")
        os.makedirs(test_dir, exist_ok=True)
        log_path = os.path.join(self.build_folder, "upstream-tests.log")
        result_path = os.path.join(self.build_folder, "upstream-test-result.json")

        packages = self._test_packages(go, env)
        self.output.info(f"yutu upstream: {len(packages)} test package(s) discovered")

        passed = failed = skipped = 0
        cases = []
        log_chunks = []
        pkg_summary = []

        for pkg in packages:
            slug = re.sub(r"[^A-Za-z0-9_.]+", "_", pkg)
            bin_path = os.path.join(test_dir, f"{slug}.test")

            compile_cmd = [go, "test", "-c", "-p", "1", "-count=1", "-timeout", "1200s",
                           "-o", bin_path, pkg]
            cp = None
            cout = ""
            for attempt in range(1, 4):
                try:
                    cp = subprocess.run(compile_cmd, cwd=self.source_folder, env=env,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        timeout=1800)
                    cout = cp.stdout.decode(errors="replace")
                except (OSError, subprocess.TimeoutExpired) as exc:
                    cp = None
                    cout = f"compile exception: {exc}"
                if (cp is not None and cp.returncode == 0) or not any(
                        marker in cout.lower() for marker in self._INFRA_MARKERS):
                    break
                if attempt < 3:
                    self.output.warning(
                        f"go test -c {pkg}: worker resource pressure, "
                        f"retry {attempt}/2 after backoff")
                    time.sleep(30 * attempt)
            if cp is None:
                pkg_summary.append(f"{pkg}: COMPILE-EXCEPTION {cout}")
                log_chunks.append(f"### go test -c {pkg}\n{cout}\n")
                failed += 1
                continue
            log_chunks.append(f"### go test -c {pkg} (exit={cp.returncode})\n{cout}\n")
            if cp.returncode != 0 or not os.path.isfile(bin_path):
                pkg_summary.append(f"{pkg}: COMPILE-FAIL exit={cp.returncode}")
                failed += 1
                continue

            self._sign_elf_if_ohos(bin_path)
            try:
                rp = subprocess.run([bin_path, "-test.v", "-test.timeout", "1200s"],
                                    cwd=self.source_folder, env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=1800)
                out = rp.stdout.decode(errors="replace")
                rc = rp.returncode
            except (OSError, subprocess.TimeoutExpired) as exc:
                pkg_summary.append(f"{pkg}: RUN-EXCEPTION {exc}")
                log_chunks.append(f"### {os.path.basename(bin_path)} -test.v\nrun exception: {exc}\n")
                failed += 1
                continue
            log_chunks.append(
                f"### {os.path.basename(bin_path)} -test.v -test.timeout 1200s (exit={rc})\n{out}\n")

            p_pass = p_fail = p_skip = 0
            for line in out.splitlines():
                stripped = line.strip()
                m = re.match(r"^--- (PASS|FAIL|SKIP): ([^ ]+)", stripped)
                if not m:
                    continue
                verdict, name = m.group(1), m.group(2)
                cases.append(f"{verdict} {pkg}::{name}")
                if verdict == "PASS":
                    p_pass += 1
                elif verdict == "FAIL":
                    p_fail += 1
                else:
                    p_skip += 1
            passed += p_pass
            failed += p_fail
            skipped += p_skip
            pkg_summary.append(f"{pkg}: pass={p_pass} fail={p_fail} skip={p_skip} exit={rc}")

        with open(log_path, "w", encoding="utf-8") as handle:
            handle.write("".join(log_chunks))

        executed = passed + failed + skipped
        for line in pkg_summary:
            self.output.info("yutu upstream | " + line)
        self.output.info(
            f"yutu upstream `go test -c` + sign + run: packages={len(packages)} "
            f"executed={executed} passed={passed} failed={failed} skipped={skipped}"
        )

        status = "failed" if failed > 0 else ("passed" if passed > 0 else "no_tests")
        upstream = {
            "status": status,
            "framework": "go-test",
            "command": ("go test -c -count=1 -timeout 1200s -o <ext2>/<pkg>.test <pkg> "
                        "&& sign <pkg>.test && <pkg>.test -test.v"),
            "packages": len(packages),
            "discovered": executed,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "cases": cases,
            "log": log_path,
            "per_package": pkg_summary,
        }
        with open(result_path, "w", encoding="utf-8") as handle:
            json.dump(upstream, handle, ensure_ascii=False, indent=1)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            {k: v for k, v in upstream.items() if k not in ("cases", "per_package")},
            ensure_ascii=False))
        self.output.info(f"yutu upstream log: {log_path}")
        if failed:
            self.output.warning(f"{failed} upstream test case(s)/package(s) did not pass")

    # ── Go toolchain helpers (aligned with aiac / abbtr / spicedb recipes) ────

    def _ensure_go_toolchain(self):
        host_arch = self._go_host_arch()
        if host_arch not in self._go_archives:
            raise ConanInvalidConfiguration(
                f"Go SDK bootstrap is not prepared for host arch: {host_arch}"
            )
        sdk_root = os.path.join(self._go_workspace(), "go-sdk", f"go{self._go_version}-{host_arch}")
        goroot = os.path.join(sdk_root, "go")
        gobin = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(gobin):
            urls, sha256 = self._go_archives[host_arch]
            self.output.info(f"Go >= {self._go_version} not found; downloading {urls[0]}")
            get(self, url=urls, sha256=sha256, destination=sdk_root, strip_root=False)
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
            candidates.extend(os.path.join(tool_dir, n) for n in os.listdir(tool_dir))
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
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; OHOS may reject unsigned executable: %s" % path
            )
            return
        tmp_dir = os.path.join(self._go_workspace(), "sign-tmp")
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)
        tmp_in = os.path.join(tmp_dir, os.path.basename(path))
        tmp_out = f"{tmp_in}.signed"
        shutil.copy2(path, tmp_in)
        objcopy = (
            os.environ.get("OHOS_LLVM_OBJCOPY")
            or shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        if os.path.isfile(objcopy):
            subprocess.run([objcopy, "--remove-section", ".codesign", tmp_in],
                           capture_output=True, timeout=30)
        subprocess.check_call([
            signer, "sign", "-selfSign", "1",
            "-inFile", tmp_in, "-outFile", tmp_out,
            "-signAlg", "SHA256withECDSA",
        ])
        shutil.move(tmp_out, path)
        os.chmod(path, 0o755)
        os.unlink(tmp_in)

    def _find_binary_sign_tool(self):
        for candidate in (
            os.environ.get("OHOS_BINARY_SIGN_TOOL"),
            os.environ.get("BINARY_SIGN_TOOL"),
            "/data/service/hnp/bin/binary-sign-tool",
            "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
            shutil.which("binary-sign-tool"),
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _goos(self):
        if str(self.settings.os) == "OHOS":
            return "linux"
        return str(self.settings.os).lower()

    def _goarch(self):
        return {
            "x86_64": "amd64",
            "x86": "386",
            "armv8": "arm64",
            "armv8_32": "arm",
            "armv7": "arm",
            "armv7hf": "arm",
            "armv6": "arm",
        }.get(str(self.settings.arch), str(self.settings.arch))

    def _go_executable(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        candidates.extend([
            os.path.expanduser("~/usr/local/go/bin/go"),
            os.path.expanduser(f"~/sdk/go{self._go_version}/bin/go"),
            os.path.expanduser(f"~/.goenv/versions/{self._go_version}/bin/go"),
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
            output = subprocess.run([go, "version"], capture_output=True, timeout=60).stdout.decode()
        except OSError:
            return False
        m = output.split("go version ")[-1].split(" ")[0]  # go1.26.5
        ver = m[2:]  # 1.26.5
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
        for candidate in (os.path.dirname(os.path.dirname(gobin)), os.environ.get("GOROOT", "")):
            if candidate and os.path.isfile(os.path.join(candidate, "bin", "go")):
                return candidate
        return ""

    def _go_workspace(self):
        if str(self.settings.os) == "OHOS":
            for base in (
                "/data/storage/el2/base/haps/entry/files",
                "/data/storage/el2/base/cache",
            ):
                candidate = os.path.join(base, f"yutu-{self.version}-go")
                try:
                    os.makedirs(candidate, exist_ok=True)
                    probe = os.path.join(candidate, ".probe")
                    Path(probe).write_text("ok\n", encoding="utf-8")
                    os.remove(probe)
                    return candidate
                except OSError:
                    continue
        root = os.path.join(self.build_folder, ".go-work")
        os.makedirs(root, exist_ok=True)
        return root
