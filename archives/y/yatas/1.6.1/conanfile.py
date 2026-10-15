#!/usr/bin/env python3
"""Conan recipe for yatas 1.6.1 — AWS/GCP infrastructure auditing CLI (pure Go).

yatas (padok-team/yatas) is a pure-Go command-line application that audits
AWS/GCP infrastructure for misconfiguration or security issues. The command
entry is the root package `github.com/padok-team/yatas` (main.go at the repo
root), so it is built with a bare `go build .`. Build with:

    CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
    GOPROXY=https://goproxy.cn,direct GOTOOLCHAIN=local \
    go build -trimpath -ldflags="-s -w" -o yatas .

Upstream 1.6.1 ships 11 `*_test.go` files with 48 top-level Go test functions
(`grep -cE '^func Test'` across the official v1.6.1 tarball = 48). The upstream
test entry per the upstream Makefile is `go test ./... -cover`. This recipe runs
all 48 upstream tests during build() by compiling each per-package test binary
with `go test -c` onto the ext2 workspace, self-signing each on OHOS with the
same binary-sign-tool path as the main binary, and exec'ing each directly with
`cwd=<package dir>` (mirrors `go test` semantics); it parses the deterministic
non-indented `--- PASS:/--- FAIL:/--- SKIP:` lines and persists the aggregate
into res/upstream_test_result.json inside the package so test_package can
re-emit HMBS_UPSTREAM_TEST_RESULT on every preflight (even when build() is
skipped on a cached binary). Running through the raw `go test ./...` *driver*
is intentionally avoided on OHOS: it collapses to a bare "FAIL" (implicit go
vet + parallel multi-binary exec under OHOS ELF-signing/fallocate).

HarmonyOS notes (identical to the proven aiac Go recipe):
- The Go linker needs an ext2-like workspace on OHOS to avoid `mapping output
  file failed: permission denied` (HMDFS mmap restriction). Link output is
  written under /data/storage/el2/base/haps/entry/files when running on OHOS.
- OHOS Go executables (and the Go SDK tool binaries themselves) must be
  self-signed with binary-sign-tool before they can be fork/exec'd.
"""
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


# OHOS `-toolexec` wrapper: after the Go linker (the `link` tool) produces an
# output binary, self-sign it with binary-sign-tool so the OHOS kernel can
# exec it. On OHOS every executed ELF (the main yatas binary here; the upstream
# test binaries are signed separately with `_sign_elf_if_ohos` after being
# compiled with `go test -c` onto the ext2 workspace) must carry a .codesign
# section. go invokes this wrapper as `<wrapper> <tool> <args...>` for every
# build tool; we only act on the `link` subcommand.
#
# This is a *shell* wrapper deliberately: `go build` (and each `go test -c`)
# invokes the wrapper for EVERY build tool (`compile`, `asm`, `vet`, `link`,
# ...) concurrently, once per package with a parallelism equal to NumCPU. A
# Python `#!/usr/bin/env python3` wrapper (which itself `subprocess.call`s the
# tool, i.e. one python + one child per tool) blows through the per-user
# process/thread limit on the ohpcd CI worker and dies with `fork/exec
# <wrapper>: resource temporarily unavailable` (EAGAIN) right at `go build`
# start. The shell wrapper removes the extra child: non-link tools are handed
# off with a plain `exec "$TOOL" "$@"` (no fork), so each concurrent tool stays
# a single short-lived process; only the single `link` step does an in-place
# self-sign. Combined with the `-p` build-parallelism cap in build(), this
# keeps peak concurrent processes small and well under the limit.
_TOOLEXEC_LINK_SIGN = r"""#!/data/service/hnp/bin/bash
set -u
TOOL="$1"
shift
if [ "$(basename "$TOOL")" != "link" ]; then
    exec "$TOOL" "$@"
fi
OUT_FILE=""
PREV=""
for A in "$@"; do
    if [ "$PREV" = "-o" ]; then
        OUT_FILE="$A"
        break
    fi
    PREV="$A"
done
"$TOOL" "$@"
RC=$?
if [ "$RC" -eq 0 ] && [ -n "$OUT_FILE" ] && [ -f "$OUT_FILE" ]; then
    SIGNER="${OHOS_BINARY_SIGN_TOOL:-${BINARY_SIGN_TOOL:-/data/service/hnp/bin/binary-sign-tool}}"
    if [ -x "$SIGNER" ]; then
        WD="${HMBS_TMPDIR:-${TMPDIR:-/tmp}}"
        TMPD="$WD/yatas-linksign"
        rm -rf "$TMPD" 2>/dev/null
        mkdir -p "$TMPD" 2>/dev/null
        cp -f "$OUT_FILE" "$TMPD/in" 2>/dev/null
        OBJCOPY="${OHOS_LLVM_OBJCOPY:-/data/service/hnp/bin/llvm-objcopy}"
        if [ -x "$OBJCOPY" ]; then
            "$OBJCOPY" --remove-section .codesign "$TMPD/in" 2>/dev/null || true
        fi
        if "$SIGNER" sign -selfSign 1 -inFile "$TMPD/in" -outFile "$TMPD/out" -signAlg SHA256withECDSA 2>/dev/null; then
            cp -f "$TMPD/out" "$OUT_FILE" 2>/dev/null
            chmod 755 "$OUT_FILE" 2>/dev/null
        fi
        rm -rf "$TMPD" 2>/dev/null
    fi
fi
exit "$RC"
"""


class YatasConan(ConanFile):
    name = "yatas"
    version = "1.6.1"
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
    package_type = "application"

    description = "A simple tool to audit AWS/GCP infrastructure for misconfiguration or potential security issues (pure Go CLI)"
    license = "Apache-2.0"
    homepage = "https://github.com/padok-team/YATAS"
    url = "https://github.com/padok-team/yatas"
    topics = ("yatas", "audit", "aws", "gcp", "security", "infrastructure", "go")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # No patches for yatas 1.6.1; kept for conandata patch export parity.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("yatas supports Linux and OHOS targets only")

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
        # Pre-create subdirs: Go refuses to bootstrap without every path component.
        for d in ("tmp", "go-build-cache", "go-mod-cache"):
            os.makedirs(os.path.join(go_workspace, d), exist_ok=True)

        gobin = self._go_executable()
        goroot = self._goroot_for_go(gobin)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(gobin))

        env.vars(self).save_script("yatas_go_env")

    def build(self):
        go = self._go_executable()
        # Build-time safety net: re-create subdirs in case generate() was skipped
        # or the workspace path changed between phases.
        for subdir in ("tmp", "go-build-cache", "go-mod-cache"):
            os.makedirs(os.path.join(self._go_workspace(), subdir), exist_ok=True)
        # On OHOS, sign every ELF the Go linker produces (main binary and the
        # per-package test binaries) so the OHOS kernel can exec them.
        toolexec_args = self._ohos_toolexec_args()
        toolexec_str = " ".join(toolexec_args)
        self.run(f'"{go}" mod download', cwd=self.source_folder, env=["yatas_go_env"])

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        # Go linker mmap fails on HMDFS: link on ext2-like workspace on OHOS.
        link_out_dir = os.path.join(self._go_workspace(), "link-out") if str(self.settings.os) == "OHOS" else out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, "yatas")
        final_exe = os.path.join(out_dir, "yatas")
        self.run(
            f'"{go}" build {toolexec_str} {self._go_build_parallel_flag()} '
            f'-trimpath -ldflags="-s -w" -o "{linked_exe}" .',
            cwd=self.source_folder,
            env=["yatas_go_env"],
        )
        # Force-re-sign the main binary with the proven python signing path.
        # The `-toolexec` shell wrapper also signs the link output in place
        # during `go build`, but that signature can be rejected by the OHOS
        # XPM exec path ("Operation not permitted", exit 126) when the packaged
        # binary is later executed from test_package. Stripping the existing
        # .codesign (the shell wrapper's) and re-signing here produces the same
        # known-good signature that the aiac recipe relies on.
        self._sign_elf_if_ohos(linked_exe, force=True)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        # ── 上游官方测试 (必做) ──
        self._run_upstream_tests(go, toolexec_args=toolexec_args)

    def package(self):
        copy(self, "yatas", os.path.join(self.build_folder, "bin"), os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # Persist upstream test evidence so test_package can re-emit the marker
        # on every preflight (build() may be skipped on a cached binary).
        result_path = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(result_path):
            copy(self, "upstream_test_result.json",
                 self.build_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ── Go toolchain helpers (aligned with spicedb / argo / aiac Go recipes) ──

    def _run_upstream_tests(self, go, toolexec_args=None):
        """Run all 48 upstream yatas Go unit tests and emit + persist HMBS evidence.

        yatas 1.6.1 ships 48 deterministic, pure-local Go top-level test
        functions across 11 ``*_test.go`` files (no network, no t.Skip, no
        t.Parallel). The official Makefile "test" target is ``go test ./...
        -cover``, which faithfully prints exactly one non-indented ``--- PASS:`` /
        ``--- FAIL:`` / ``--- SKIP:`` line per top-level test function.

        On HarmonyOS, the ``go test ./...`` *driver* is not reliably exec-able: it
        links several per-package test binaries and runs them through an implicit
        ``go vet`` + parallel multi-binary exec path that is fragile under the OHOS
        ELF signing / fallocate restrictions (on the real worker it collapses to a
        bare "FAIL" with no per-package detail). The main executable, by contrast,
        is proven to build and run on OHOS when its link output is placed on an
        ext2-like workspace and the ELF is self-signed with binary-sign-tool.

        To make the upstream suite run reliably on OHOS while staying faithful to
        the same 48 test functions and the same ``--- PASS/F/SKIP`` output, we:
          1. discover the test packages from ``*_test.go`` files under source,
          2. compile each test binary with ``go test -c -o <ext2-workspace>/<slug>.test
             ./<pkg>`` (single link onto the writable ext2 workspace; no driver,
             no vet, no parallel multi-binary exec),
          3. on OHOS self-sign each test binary with the *same* ``_sign_elf_if_ohos``
             that makes the working main binary exec-able,
          4. exec each test binary directly with ``cwd = <package dir>`` (exactly
             the cwd ``go test`` uses, so relative fixtures resolve) and parse the
             non-indented ``--- PASS/F/SKIP:`` lines.

        Counts come from exactly one deterministic source (the non-indented
        per-top-level-test lines in the real test-binary output); no subtraction
        or guessing. The aggregate mark is persisted to upstream_test_result.json
        for the test_package to re-emit on every preflight.
        """
        del toolexec_args  # tests do not use the -toolexec driver path (unused)
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
        signer = self._find_binary_sign_tool()
        if signer:
            base_env["OHOS_BINARY_SIGN_TOOL"] = signer

        # 1. discover test packages from *_test.go files under source.
        src = Path(self.source_folder)
        test_dirs = []
        seen = set()
        for tf in src.rglob("*_test.go"):
            rel_dir = tf.parent.relative_to(src)
            if any(part.startswith(".") for part in rel_dir.parts):
                continue  # skip hidden/vendor dirs
            key = str(rel_dir)
            if key not in seen:
                seen.add(key)
                test_dirs.append(key)
        test_dirs.sort()

        test_bin_dir = os.path.join(go_workspace, "test-bin")
        os.makedirs(test_bin_dir, exist_ok=True)

        passed = failed = skipped = 0
        run_failures = []
        command_parts = [
            f'"{go}" mod download',
        ]
        all_output = []

        for rel in test_dirs:
            slug = rel.replace("/", "-") or "root"
            test_bin = os.path.join(test_bin_dir, slug + ".test")
            pkg_arg = "./" + rel if rel != "." else "."
            # 2. compile a single test binary (link output lands on ext2 workspace).
            # NOTE: the `-p` build-parallelism cap is NOT applied here. `go test
            # -c` rejects `-p` ("go: unknown flag -p N cannot be used with -c"):
            # `-p` is only accepted by `go build`/`go run`, never with `-c`
            # (verified against the 1.26.5 test failure in the preflight log).
            # We compile one package at a time anyway, so there is no burst of
            # concurrent `-toolexec` wrappers to cap during test-binary compile.
            cc = [go, "test", "-c", "-o", test_bin, pkg_arg]
            command_parts.append(" ".join([f'"{a}"' if os.sep in a else a for a in cc]))
            try:
                proc = subprocess.run(cc, cwd=self.source_folder, env=base_env,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1200)
                bc_out = proc.stdout.decode(errors="replace")
            except (OSError, subprocess.TimeoutExpired) as exc:
                bc_out = "go test -c failed to run: %s" % exc
            if not os.path.isfile(test_bin):
                # Honest diagnostic: this package's test binary could not be built.
                run_failures.append((rel, bc_out))
                all_output.append("GO TEST -c %s FAILED (no test binary):\n%s" % (rel, bc_out))
                continue
            # 3. sign the test binary with the proven main-binary path (OHOS only).
            self._sign_elf_if_ohos(test_bin)
            # 4. exec it directly with cwd = package dir (mirrors `go test`).
            pkg_dir = os.path.join(self.source_folder, rel)
            run_cmd = [test_bin, "-test.v", "-test.count=1"]
            command_parts.append(" ".join([f'"{a}"' for a in run_cmd]) +
                                 ("  # cwd=" + pkg_dir))
            try:
                proc = subprocess.run(run_cmd, cwd=pkg_dir, env=base_env,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1200)
                out = proc.stdout.decode(errors="replace")
            except (OSError, subprocess.TimeoutExpired) as exc:
                out = "test binary failed to run: %s" % exc
            all_output.append("=== package %s ===\n%s" % (rel, out))
            # Deterministic parse of non-indented per-top-level-test lines only.
            p = len(re.findall(r"^--- PASS:", out, re.MULTILINE))
            f = len(re.findall(r"^--- FAIL:", out, re.MULTILINE))
            s = len(re.findall(r"^--- SKIP:", out, re.MULTILINE))
            passed += p
            failed += f
            skipped += s
            self.output.info("yatas upstream %s: PASS=%d FAIL=%d SKIP=%d" %
                             (rel, p, f, s))

        executed = passed + failed + skipped

        combined_out = "\n".join(all_output)
        self.output.info("yatas upstream aggregate: "
                         f"PASS={passed} FAIL={failed} SKIP={skipped} "
                         f"executed={executed} packages={test_dirs!r}")
        preview = combined_out[:4096].replace("\n", "\n  yatas go test | ")
        self.output.info("yatas go test output preview:\n  " + preview)

        gaps = []
        declared_total = 48  # official go_test_functions count (MANIFEST)
        not_run = declared_total - passed
        if not_run > 0:
            # Real, honest gap: some of the audited 48 upstream tests did not
            # emit a PASS line (a package's test binary could not be built/run,
            # or a test failed). gaps total == discovered - passed, so the
            # marker never contradicts itself.
            detail = ("%d of the audited %d upstream tests did not pass (PASS=%d)"
                      % (not_run, declared_total, passed))
            if run_failures:
                detail += "; packages whose test binary could not be executed: " + \
                          ", ".join(rel for rel, _ in run_failures)
            gaps.append({
                "count": not_run,
                "category": "test_failure",
                "detail": detail,
                "evidence": (combined_out[:1500]
                             or "; ".join(err for _, err in run_failures)[:1500]),
            })

        if failed > 0:
            status = "failed"
        elif passed == declared_total:
            status = "passed"
        elif passed > 0:
            status = "incomplete"
        elif not test_dirs:
            status = "no_tests"
        else:
            status = "failed"

        discovered = declared_total
        upstream = {
            "status": status,
            "framework": "go test",
            "command": " ; ".join(command_parts),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if gaps:
            upstream["gaps"] = gaps
        json_str = json.dumps(upstream, ensure_ascii=False)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json_str)

        # Persist for test_package re-emission across preflight runs.
        result_file = os.path.join(self.build_folder, "upstream_test_result.json")
        Path(result_file).write_text(json_str, encoding="utf-8")
        self.output.info("yatas upstream test result persisted to %s" % result_file)

    def _go_workspace(self):
        if str(self.settings.os) == "OHOS":
            for base in (
                "/data/storage/el2/base/haps/entry/files",
                "/data/storage/el2/base/cache",
            ):
                candidate = os.path.join(base, "yatas-1.6.1-go")
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

    def _ohos_toolexec_args(self):
        """Return ``["-toolexec", <wrapper>]`` on OHOS (else ``[]``).

        The `-toolexec` wrapper signs the ELF produced by the Go linker for the
        main ``go build`` step (the upstream test binaries are instead compiled
        to the ext2 workspace with ``go test -c`` and signed via
        ``_sign_elf_if_ohos`` in ``_run_upstream_tests``). On OHOS unsigned
        ELFs cannot fork/exec. This is the same OHOS `-toolexec` mechanism
        proven by the osv-scanner recipe.
        """
        if str(self.settings.os) != "OHOS":
            return []
        wrapper = os.path.join(self._go_workspace(), "toolexec_link_sign.sh")
        try:
            existing = Path(wrapper).read_text(encoding="utf-8") if os.path.isfile(wrapper) else ""
        except OSError:
            existing = ""
        if existing != _TOOLEXEC_LINK_SIGN:
            Path(wrapper).write_text(_TOOLEXEC_LINK_SIGN, encoding="utf-8")
            os.chmod(wrapper, 0o755)
        signer = self._find_binary_sign_tool()
        if signer:
            os.environ["OHOS_BINARY_SIGN_TOOL"] = signer
        return ["-toolexec", wrapper]

    def _go_build_parallel_flag(self):
        """Return ``-p <N>`` to cap Go build tool parallelism on OHOS (else \"\").

        `go build` (and `go test -c`) run one tool (`compile`, `asm`, `link`,
        ...) per dependency package *in parallel with a concurrency equal to
        NumCPU*, and on OHOS each tool invocation goes through the
        `-toolexec` shell wrapper. On high-core-count ohpcd CI workers the
        resulting burst of concurrent wrapper/tool processes can exceed the
        per-user process/thread limit and abort with `resource temporarily
        unavailable` (EAGAIN) at `go build` start. Capping the tool parallelism
        to a small fixed value keeps peak concurrent processes tiny and well
        under the limit; correctness is unaffected, only wall-clock speed.
        """
        if str(self.settings.os) != "OHOS":
            return ""
        return "-p 4"

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

    def _sign_elf_if_ohos(self, path, force=False):
        if str(self.settings.os) != "OHOS":
            return
        if not force and self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; OHOS may reject unsigned executable: %s" % path
            )
            return
        # Always strip any pre-existing .codesign (even when force=True) so the
        # output carries a fresh, currently-valid signature. On OHOS a .codesign
        # section written at an earlier phase (e.g. by the `-toolexec` shell
        # wrapper during `go build`) can be rejected by the XPM exec path with
        # "Operation not permitted" (exit 126) at a later exec; re-signing here
        # with the proven path removes the stale section and re-signs from the
        # unsigned ELF (same remove-and-resign as the aiac recipe that this
        # signing path is copied from).
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

    def _find_binary_sign_tool(self):
        """Return the path to binary-sign-tool, or None if unavailable."""
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

    def _go_executable(self):
        candidates = []
        if os.environ.get("GO"):
            candidates.append(os.environ["GO"])
        if os.environ.get("GOROOT"):
            candidates.append(os.path.join(os.environ["GOROOT"], "bin", "go"))
        candidates.extend([
            os.path.expanduser("~/usr/local/go/bin/go"),
            os.path.expanduser("~/sdk/go1.26.5/bin/go"),
            os.path.expanduser("~/.goenv/versions/1.26.5/bin/go"),
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
        candidates = [
            os.path.dirname(os.path.dirname(gobin)),
            os.environ.get("GOROOT", ""),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(os.path.join(candidate, "bin", "go")):
                return candidate
        return ""
