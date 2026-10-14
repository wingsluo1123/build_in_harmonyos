#!/usr/bin/env python3
"""Conan recipe for typeshare 1.13.4 (HarmonyOS / OpenHarmony PC, aarch64).

typeshare is a pure-Rust CLI that generates Typescript / Swift / Kotlin / Scala /
Go / Python type definitions from annotated Rust source (upstream
https://github.com/1Password/typeshare, crate ``typeshare-cli`` with binary
``typeshare``).

Cross-compiled for aarch64-unknown-linux-ohos with the Rust toolchain shipped by
the ``rust-toolchain/1.97.1`` infrastructure package (tool_requires).  No rustup
bootstrap is attempted: stock rustup cannot recognise a HarmonyOS host
("unrecognized OS type: HarmonyOS", knowledge E105/E154).

Why the recipe does what it does
--------------------------------
* OHOS refuses to execve an unsigned ELF and the rust-lang dist tarball inside
  rust-toolchain/1.97.1 carries no code signature, so ``cargo``/``rustc`` fail
  with EACCES (errno 13).  The recipe copies ``cargo``/``rustc`` plus the
  ``librustc_driver`` dylib rustc dlopens into the build folder, signs them with
  ``binary-sign-tool -selfSign 1`` and symlinks the remaining read-only payload
  (below/0.11.0, rumdl/0.2.39 precedent).
* ``cargo`` dynamically links ``libssl``/``libcrypto``/``libz`` while the OHOS
  loader ignores DT_RUNPATH, so the OpenSSL pair comes from the Harmonybrew OHOS
  bottle and is placed on ``LD_LIBRARY_PATH`` (rumdl/0.2.39 precedent).  ``libz``
  needs no extra source: the OS image provides it (``/usr/lib/libz.so.1``);
  the third-party ``zlib-ng-compat`` bottle was removed because a rotating CDN
  artifact must not be a hard build dependency (CI worker got a 404 for it).
  ``librustc_driver`` additionally needs the OHOS ``libc++_shared.so``, which the
  loader does not find in the SDK arch sub-directory, so a signed copy is put on
  ``LD_LIBRARY_PATH`` as well.
* The device has no default CA store, so a CA bundle is located and exported for
  the rsproxy.cn crates mirror.
* HarmonyOS ``/tmp`` is read-only (E002), so TMPDIR points at a writable dir.

Dependencies
------------
typeshare has no external C/C++ target dependency: the whole 110-package
dependency closure is pure Rust (crates.io via rsproxy.cn, all pinned by
``Cargo.lock``).  The only ``-sys`` crates in the lock file are platform-gated
(core-foundation-sys/macOS, js-sys/wasm, windows-sys/Windows) or pure-Rust
(linux-raw-sys); none is built for OHOS.

Upstream tests
--------------
``build()`` runs the whole upstream suite so every CI run re-runs it:
``cargo test --release --locked --target <ohos> --workspace --all-features
--tests`` (upstream CI gate ``cargo test --all-features``: unit tests of all four
workspace members plus the ``core/tests`` integration suites), plus a faithful
execution of the repository's shell-driven determinism sample
(``tests/justfile``).  Doc-tests are excluded because rust-toolchain/1.97.1 ships
no ``rustdoc`` binary.  ``OHC_SKIP_UPSTREAM_TESTS=1`` is the CI escape hatch.

The *shipped* binary keeps cargo's default features (Kotlin/Scala/Swift/
TypeScript), matching ``cargo install typeshare-cli`` and the cargo-dist release
artifacts; Go/Python are documented as experimental opt-in features
(README: "Enable the `go` or `python` features ... if you want to use these").
"""

import os
import re
import shlex
import shutil
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# cargo's runtime shared libraries (the OHOS loader ignores DT_RUNPATH, so they
# must be on LD_LIBRARY_PATH).  Harmonybrew OHOS bottle, sha256 measured on the
# real machine from the published artifact.
#
# Only OpenSSL is provided here on purpose: `readelf -d cargo` also lists
# `libz.so`, but that one is satisfied by the OS image itself
# (`/usr/lib/libz.so.1`; verified: the toolchain `cargo` runs with no external
# libz on LD_LIBRARY_PATH), so a third-party zlib bottle is NOT required.
# The `zlib-ng-compat` bottle used earlier was removed after the CI worker got
# `NotFoundException: Not found: .../zlib-ng-compat-2.3.3_2.arm64_ohos.bottle.tar.gz`
# while the same URL answered 200 locally — harmonybrew revisions rotate and the
# CDN is not uniformly replicated; depending on it made the build flaky for an
# artifact the platform already provides.
#
# OpenSSL cannot be dropped the same way: the system `/usr/lib/libssl.so.3`
# lacks `SSL_get0_group_name` (cargo 1.97 requires >= 3.5) and the registry
# `openssl/3.5.8.1` package is static-only (`shared: False`), so the bottle is
# the only usable source of `libssl.so`/`libcrypto.so` for the toolchain.
RUST_RUNTIME_BOTTLES = (
    ("openssl3",
     "https://harmonybrew.atomgit.com/bottles/"
     "openssl%403-3.6.5.arm64_ohos.bottle.tar.gz",
     "f8c374560f0002975203425b6b5db30f84eb9e78f9c56a8494b60ca57664327c"),
)

BINARY_NAME = "typeshare"
CRATE_NAME = "typeshare-cli"

# HMDFS write-then-exec race markers (see knowledge
# DRAFT-hmdfs-etxtbsy-write-then-exec-cargo-retry): only these trigger a retry.
ETXTBSY_MARKERS = ("Text file busy", "os error 26")


class TypeshareConan(ConanFile):
    name = "typeshare"
    version = "1.13.4"
    description = ("Command line tool for generating language files with "
                   "typeshare")
    license = "MIT OR Apache-2.0"
    homepage = "https://github.com/1Password/typeshare"
    url = "https://github.com/1Password/typeshare"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        self._ohos_target()

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # Rust toolchain from the registry infrastructure package (R36: publish
        # dependencies before building downstream).  rust-lang official dist
        # tarball, host & target both aarch64-unknown-linux-ohos.
        self.tool_requires("rust-toolchain/1.97.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        env = self._rust_environment()
        self._ensure_ohos_target(env)
        self._fetch_cargo_deps(env)
        self._run_upstream_tests(env)
        self._cargo_build(env)
        # after the release build: reuse those artifacts instead of spawning a
        # fresh (debug) cargo build just for the determinism sample
        self._run_upstream_determinism_test(env)
        self._sign_binaries()

    # ── build helpers ──────────────────────────────────────────────────

    def _ohos_target(self):
        arch = str(self.settings.arch)
        mapping = {
            "armv8": "aarch64-unknown-linux-ohos",
            "arm64": "aarch64-unknown-linux-ohos",
            "aarch64": "aarch64-unknown-linux-ohos",
            "armv7": "armv7-unknown-linux-ohos",
            "x86_64": "x86_64-unknown-linux-ohos",
        }
        target = mapping.get(arch)
        if not target:
            raise ConanInvalidConfiguration(f"Unsupported arch: {arch}")
        return target

    def _rust_environment(self):
        env = os.environ.copy()
        cargo = self._find_cargo(env)
        env["CARGO"] = cargo
        extra_paths = [os.path.dirname(cargo)]
        extra_paths += [d for d in ("/system/bin", "/system/sbin", "/vendor/bin")
                        if os.path.isdir(d)]
        env["PATH"] = os.pathsep.join(extra_paths) + os.pathsep + env.get("PATH", "")
        # toolchain-private lib (signed librustc_driver + symlinked payload),
        # cargo runtime libs (libssl/libcrypto/libz) and signed libc++_shared.so
        lib_dirs = [os.path.join(self._toolchain_dir(), "lib")]
        lib_dirs += self._prepare_runtime_libs()
        cxx_shared = self._prepare_cxx_shared()
        if cxx_shared:
            lib_dirs.append(cxx_shared)
        if lib_dirs:
            prev = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                lib_dirs + ([prev] if prev else [])
            )
        self._prepare_test_runner(env)
        ca = self._ca_bundle()
        if ca:
            env["SSL_CERT_FILE"] = ca
            env["CURL_CA_BUNDLE"] = ca
        cargo_home = env.get("CARGO_HOME") or os.path.expanduser("~/.cargo")
        os.makedirs(cargo_home, exist_ok=True)
        self._configure_rsproxy(cargo_home, ca)
        env["CARGO_HOME"] = cargo_home
        self._ensure_writable_tmpdir(env)
        if self.settings.os == "OHOS":
            cc = self._ohos_cc()
            env.update({
                "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER": cc,
                "CC_aarch64_unknown_linux_ohos": cc,
                "CXX_aarch64_unknown_linux_ohos": self._ohos_cxx(),
                "AR_aarch64_unknown_linux_ohos": self._llvm_ar(),
                "RANLIB_aarch64_unknown_linux_ohos": self._llvm_ranlib(),
            })
        return env

    def _fetch_cargo_deps(self, env):
        """Materialise the pinned crate graph before touching the compiler.

        ``Cargo.lock`` is complete (110 packages, no git dependencies), so a
        single ``cargo fetch --locked`` resolves everything; afterwards the
        build and the test runs need no further network access.
        """
        result = subprocess.run(
            [env["CARGO"], "fetch", "--locked",
             "--manifest-path", os.path.join(self.source_folder, "Cargo.toml")],
            cwd=self.source_folder, env=env,
        ).returncode
        if result != 0:
            raise ConanInvalidConfiguration(f"cargo fetch failed (rc={result})")

    def _prepare_test_runner(self, env):
        """Install a cargo target-runner that puts the *signed* dylibs first.

        When cargo launches a test binary it prepends
        ``<sysroot>/lib/rustlib/<target>/lib`` to ``LD_LIBRARY_PATH``.  That
        directory is the read-only toolchain payload, so the ``libstd-*.so``
        living there is **unsigned** — and OHOS refuses to load an unsigned
        shared library.  Every harness linked with ``prefer-dynamic`` (proc-macro
        crates such as ``typeshare-annotation``) therefore dies with
        ``Error loading shared library libstd-<hash>.so`` followed by
        "symbol not found" relocation errors and exit status 127.

        The signed copies produced by ``_prepare_signed_toolchain()`` sit in the
        toolchain lib dir, but cargo's prepended path shadows them.  This runner
        re-orders the search path so the signed ones are found first.  It is a
        build-environment adaptation only — upstream sources stay untouched and
        the shipped binary is not affected (it is linked statically and has no
        ``libstd`` dependency).

        The runner must live in a path without spaces: cargo passes the runner
        value through a whitespace split when executing it.
        """
        runner = os.path.join(self.build_folder, "ohos-test-runner.sh")
        with open(runner, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("#!/bin/sh\n"
                     'export LD_LIBRARY_PATH="%s:$LD_LIBRARY_PATH"\n'
                     'exec "$@"\n' % env["LD_LIBRARY_PATH"])
        os.chmod(runner, 0o755)
        var = "CARGO_TARGET_%s_RUNNER" % self._ohos_target().upper().replace("-", "_")
        env[var] = runner
        self.output.info("test runner installed: %s" % var)

    def _ensure_writable_tmpdir(self, env):
        current = env.get("TMPDIR")
        if current and os.path.isdir(current) and os.access(current, os.W_OK):
            return
        fallback = os.path.expanduser("~/tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            fallback = self.build_folder
        env["TMPDIR"] = fallback
        self.output.info(f"TMPDIR set to {fallback} (OHOS /tmp is read-only)")

    def _ohos_cc(self):
        candidates = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/"
            "aarch64-unknown-linux-ohos-clang",
            shutil.which("aarch64-unknown-linux-ohos-clang"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        raise ConanInvalidConfiguration("aarch64-unknown-linux-ohos-clang not found")

    def _ohos_cxx(self):
        cc = self._ohos_cc()
        return cc + "++" if not cc.endswith("++") else cc

    def _llvm_ar(self):
        return os.path.join(os.path.dirname(self._ohos_cc()), "llvm-ar")

    def _llvm_ranlib(self):
        return os.path.join(os.path.dirname(self._ohos_cc()), "llvm-ranlib")

    def _ensure_ohos_target(self, env):
        target = self._ohos_target()
        rustc = os.path.join(os.path.dirname(env["CARGO"]), "rustc")
        if not os.path.isfile(rustc):
            rustc = shutil.which("rustc") or ""
        if not rustc:
            return
        prefix = os.path.dirname(os.path.dirname(rustc))
        rustlib = os.path.join(prefix, "lib", "rustlib", target)
        if not os.path.isdir(rustlib):
            self.output.warning(
                f"rust-std for {target} not found under {rustlib}; "
                "the toolchain may be unable to build for OHOS")

    def _run_cargo(self, env, cmd, log_path=None):
        """Run a cargo subprocess, retrying **once** only on the HMDFS ETXTBSY flake.

        On OHOS/HMDFS cargo's "write build-script then exec it" path intermittently
        fails with ``Text file busy (os error 26)`` ("could not execute process
        ... (never executed)") — see knowledge
        ``DRAFT-hmdfs-etxtbsy-write-then-exec-cargo-retry``.  The retry is anchored
        to that error text on purpose: a genuine compile/test error does not
        contain it, so real failures are never masked or retried.
        """
        rc, text = 1, ""
        for attempt in (1, 2):
            if log_path:
                with open(log_path, "wb" if attempt == 1 else "ab") as fh:
                    rc = subprocess.run(cmd, cwd=self.source_folder, env=env,
                                        stdout=fh,
                                        stderr=subprocess.STDOUT).returncode
                text = open(log_path, encoding="utf-8",
                            errors="replace").read()
            else:
                proc = subprocess.run(cmd, cwd=self.source_folder, env=env,
                                      capture_output=True, text=True)
                rc = proc.returncode
                text = (proc.stdout or "") + (proc.stderr or "")
            if rc == 0 or attempt == 2:
                break
            if not any(m in text for m in ETXTBSY_MARKERS):
                break
            self.output.warning(
                "ETXTBSY (HMDFS write-then-exec race) — retrying once")
        return rc, text

    # ── upstream tests ─────────────────────────────────────────────────

    def _run_upstream_tests(self, env):
        """Run the upstream cargo test suite for the whole workspace.

        ``--workspace --all-features --tests`` mirrors the upstream CI gate
        (``.github/workflows/ci.yml``: ``cargo test --all-features``) and covers
        every ``#[test]`` of the four workspace members (``typeshare-annotation``,
        ``typeshare-core``, ``typeshare``, ``typeshare-cli``) plus the
        ``core/tests`` integration suites (``agnostic_tests.rs``,
        ``snapshot_tests.rs`` — the snapshot suite is expanded from the
        ``tests!`` macro over ``core/data/tests/**``).  ``--all-features`` also
        enables the experimental Go/Python generators so their snapshot cases
        run.  Doc-tests are excluded because rust-toolchain/1.97.1 ships no
        rustdoc.  See test_package/MANIFEST.yml and notes.md for the accounting.
        """
        if os.environ.get("OHC_SKIP_UPSTREAM_TESTS") == "1":
            self.output.info(
                "Skipping upstream cargo test (OHC_SKIP_UPSTREAM_TESTS=1); "
                "suite validated in notes.md/reports.")
            return
        target = self._ohos_target()
        log = os.path.join(self.build_folder, "cargo_test.log")
        cmd = [env["CARGO"], "test", "--release", "--locked",
               "--target", target, "--workspace", "--all-features",
               "--tests", "--no-fail-fast"]
        self.output.info("Running upstream tests: %s" % " ".join(cmd))
        result, _text = self._run_cargo(env, cmd, log_path=log)
        self._report_test_summary(log, result)
        if result != 0:
            raise ConanInvalidConfiguration(
                f"Upstream typeshare tests failed for {target} (rc={result}); "
                f"see {log}")

    def _run_upstream_determinism_test(self, env):
        """Execute the repository's shell-driven determinism sample.

        ``tests/justfile`` (``just determinism``) generates 100 Rust inputs from
        ``tests/data/determinism-base.rs``, runs the CLI twice over the same
        directory and requires byte-identical output.  ``just``/``sd`` are not
        part of the OHOS image (``sed`` is not reliably on the build PATH
        either), so the recipe replays the very same steps with the Python
        standard library — the substitution is the identical global regex
        ``(struct )(\\w+)`` → ``\\1\\2<i>`` — and asserts the same property.

        The CLI is launched through ``cargo run -p typeshare-cli`` exactly as
        the justfile does, but with ``--release --locked --target <ohos>`` and
        only after ``_cargo_build()``: that reuses the artifacts of this build
        instead of spawning a second, from-scratch debug build.  On OHOS/HMDFS a
        freshly written build-script executable can still be open for writing
        when cargo execs it, which randomly fails with ``Text file busy
        (os error 26)`` (observed once in a ``conan create`` run); reusing the
        release artifacts removes that path entirely.  Determinism of the
        generated output does not depend on the cargo profile.
        """
        if os.environ.get("OHC_SKIP_UPSTREAM_TESTS") == "1":
            return
        base = os.path.join(self.source_folder, "tests", "data",
                            "determinism-base.rs")
        if not os.path.isfile(base):
            self.output.warning(f"determinism sample absent: {base}")
            return
        work = os.path.join(self.build_folder, "determinism")
        in_dir = os.path.join(work, "input")
        out_dir = os.path.join(work, "out")
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)
        with open(base, encoding="utf-8") as fh:
            template = fh.read()
        # tests/justfile uses `sd '(struct )(\w+)' "\1\2<i>"`; the OHOS image has
        # no `sd` (and no reliably reachable `sed`), so the same global
        # substitution is done in Python — byte-for-byte equivalent output.
        for i in range(1, 101):  # tests/justfile: determinism_qty := '100'
            rendered = re.sub(r"(struct )(\w+)",
                              lambda m, n=i: m.group(1) + m.group(2) + str(n),
                              template)
            with open(os.path.join(in_dir, f"input{i}.rs"), "w",
                      encoding="utf-8", newline="\n") as fh:
                fh.write(rendered)
        log = os.path.join(self.build_folder, "determinism.log")
        with open(log, "wb") as fh:
            for out_name in ("output1.ts", "output2.ts"):
                rc = subprocess.run(
                    [env["CARGO"], "run", "--release", "--locked",
                     "--target", self._ohos_target(), "-p", CRATE_NAME, "--",
                     "-l", "typescript", "-o",
                     os.path.join(out_dir, out_name), in_dir],
                    cwd=self.source_folder, env=env,
                    stdout=fh, stderr=subprocess.STDOUT).returncode
                if rc != 0:
                    raise ConanInvalidConfiguration(
                        f"determinism sample: typeshare run failed (rc={rc}), "
                        f"see {log}")
        # `diff -q out/*.ts` from tests/justfile, without depending on diff(1).
        first = os.path.join(out_dir, "output1.ts")
        second = os.path.join(out_dir, "output2.ts")
        with open(first, "rb") as fh:
            a = fh.read()
        with open(second, "rb") as fh:
            b = fh.read()
        if a != b:
            raise ConanInvalidConfiguration(
                "determinism sample: two identical runs diverged "
                f"({len(a)} vs {len(b)} bytes), see {log}")
        self.output.info(
            "determinism sample OK: 100 inputs, two runs byte-identical "
            f"({len(a)} bytes), log: {log}")

    def _report_test_summary(self, log, rc):
        """Print the cargo test summary into the conan output for the record."""
        try:
            with open(log, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            self.output.warning(f"cargo test log not readable: {log}")
            return
        summary = [ln.rstrip("\n") for ln in lines if "test result:" in ln]
        self.output.info("upstream cargo test rc=%s; log: %s" % (rc, log))
        for ln in summary:
            self.output.info("    " + ln)

    # ── build ──────────────────────────────────────────────────────────

    def _cargo_build(self, env):
        # Default features only, matching `cargo install typeshare-cli` and the
        # upstream cargo-dist release artifacts (Go/Python are experimental
        # opt-in features, see the module docstring).
        target = self._ohos_target()
        cmd = [env["CARGO"], "build", "--release", "--locked",
               "--target", target, "-p", CRATE_NAME]
        result, _text = self._run_cargo(
            env, cmd, log_path=os.path.join(self.build_folder, "cargo_build.log"))
        if result != 0:
            raise ConanInvalidConfiguration(
                f"cargo build failed for {target} (rc={result})")
        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "target", target, "release",
                           BINARY_NAME)
        if not os.path.isfile(src):
            raise ConanInvalidConfiguration(
                f"{BINARY_NAME} binary not produced: {src}")
        dst = os.path.join(out_dir, BINARY_NAME)
        shutil.copy2(src, dst)
        os.chmod(dst, 0o755)

    def _sign_binaries(self):
        if self.settings.os != "OHOS":
            return
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; OHOS may reject executables")
            return
        out_dir = os.path.join(self.build_folder, "bin")
        for name in os.listdir(out_dir):
            path = os.path.join(out_dir, name)
            if os.path.isfile(path):
                result = self.run(
                    f"{shlex.quote(signer)} sign "
                    f"-inFile {shlex.quote(path)} "
                    f"-outFile {shlex.quote(path)} -selfSign 1",
                    ignore_errors=True, quiet=True,
                )
                if result != 0:
                    raise ConanInvalidConfiguration(
                        f"binary-sign-tool failed (rc={result}): {path}")

    def _find_binary_sign_tool(self):
        candidates = [
            os.environ.get("BINARY_SIGN_TOOL"),
            shutil.which("binary-sign-tool"),
            shutil.which("hapsign"),
            "/data/service/hnp/bin/binary-sign-tool",
            "/data/service/hnp/ohos-sdk.org/"
            "ohos-sdk_26.0.0.18/ohos/native/bin/binary-sign-tool",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    # ── toolchain discovery / bootstrap ────────────────────────────────

    def _find_cargo(self, env):
        candidates = [
            os.environ.get("CARGO"),
            env.get("CARGO"),
            shutil.which("cargo"),
            os.path.expanduser("~/.cargo/bin/cargo"),
            os.path.expanduser("~/.harmonybrew/bin/cargo"),
            "/data/service/hnp/bin/cargo",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        bin_dir = self._prepare_signed_toolchain()
        candidate = os.path.join(bin_dir, "cargo")
        if os.path.isfile(candidate):
            return candidate
        raise ConanInvalidConfiguration(
            "Rust/Cargo toolchain not found: no system cargo and no "
            "rust-toolchain/1.97.1 tool_requires package available")

    def _rust_toolchain_dep(self):
        try:
            return self.dependencies.build.get("rust-toolchain")
        except (KeyError, ConanInvalidConfiguration):
            return None

    def _toolchain_dir(self):
        return os.path.join(self.build_folder, "rust-toolchain")

    def _prepare_signed_toolchain(self):
        """Prepare an executable (signed) Rust toolchain; return its bin dir."""
        dst = self._toolchain_dir()
        bin_dst = os.path.join(dst, "bin")
        lib_dst = os.path.join(dst, "lib")
        marker = os.path.join(dst, ".prepared")
        if os.path.isfile(marker):
            return bin_dst
        tool = self._rust_toolchain_dep()
        if not tool:
            raise ConanInvalidConfiguration(
                "rust-toolchain/1.97.1 tool_requires package not available")
        src = tool.package_folder
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)

        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; toolchain binaries stay unsigned "
                "and may be rejected by the OHOS loader (EACCES)")

        to_sign = []
        for name in ("cargo", "rustc"):
            s = os.path.join(src, "bin", name)
            if os.path.isfile(s):
                d = os.path.join(bin_dst, name)
                if not os.path.isfile(d):
                    shutil.copy2(s, d)
                    os.chmod(d, 0o755)
                to_sign.append(d)
        src_lib = os.path.join(src, "lib")
        dylib_srcs = []
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                if name.startswith("librustc_driver") and name.endswith(".so"):
                    dylib_srcs.append(os.path.join(src_lib, name))
            # proc-macro crates' unit-test harnesses are linked with
            # `prefer-dynamic`, so they DT_NEEDED `libstd-*.so` which lives in
            # `lib/rustlib/<target>/lib/`.  The OHOS loader searches no
            # sub-directory, so those dylibs are copied + signed *flat* into the
            # toolchain lib dir (which is on LD_LIBRARY_PATH); without this the
            # `typeshare-annotation` test harness dies with
            # "Error loading shared library libstd-<hash>.so" (exit 127).
            rustlib_lib = os.path.join(src_lib, "rustlib", self._ohos_target(),
                                      "lib")
            if os.path.isdir(rustlib_lib):
                for name in sorted(os.listdir(rustlib_lib)):
                    if name.endswith(".so"):
                        dylib_srcs.append(os.path.join(rustlib_lib, name))
        for s in dylib_srcs:
            d = os.path.join(lib_dst, os.path.basename(s))
            if not os.path.isfile(d):
                shutil.copy2(s, d)
                os.chmod(d, 0o755)
            to_sign.append(d)

        if signer:
            for path in to_sign:
                tmp = path + ".signed"
                result = subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", tmp,
                     "-selfSign", "1"],
                    capture_output=True, text=True,
                )
                if result.returncode != 0 or not os.path.isfile(tmp):
                    raise ConanInvalidConfiguration(
                        "binary-sign-tool failed for %s (rc=%d): %s"
                        % (path, result.returncode, result.stderr[:200])
                    )
                os.replace(tmp, path)
                os.chmod(path, 0o755)
                self.output.info("signed toolchain binary: %s"
                                 % os.path.basename(path))
        else:
            self.output.warning("toolchain binaries were not signed")

        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                d = os.path.join(lib_dst, name)
                if not os.path.exists(d):
                    self._link_or_copy(os.path.join(src_lib, name), d)
        for name in ("etc", "libexec", "share"):
            s = os.path.join(src, name)
            d = os.path.join(dst, name)
            if os.path.isdir(s) and not os.path.exists(d):
                self._link_or_copy(s, d)

        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("signed toolchain prepared\n")
        return bin_dst

    def _link_or_copy(self, src, dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            os.symlink(src, dst)
            return
        except OSError:
            pass
        if os.path.isdir(src):
            shutil.copytree(src, dst, symlinks=True)
        else:
            shutil.copy2(src, dst)

    def _prepare_cxx_shared(self):
        """Return a directory holding an executable OHOS ``libc++_shared.so``.

        ``librustc_driver`` is dynamically linked against the OHOS C++ runtime;
        the OHOS loader does not search the SDK's arch sub-directories, so a
        signed copy is placed next to the toolchain libs and put on
        LD_LIBRARY_PATH.
        """
        marker_dir = os.path.join(self.build_folder, "cxx-shared")
        dest = os.path.join(marker_dir, "libc++_shared.so")
        if os.path.isfile(dest):
            return marker_dir
        candidates = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/"
            "lib/aarch64-linux-ohos/libc++_shared.so",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/"
            "lib/aarch64-linux-ohos/c++/libc++_shared.so",
        ]
        src = next((c for c in candidates if os.path.isfile(c)), None)
        if not src:
            return None
        os.makedirs(marker_dir, exist_ok=True)
        shutil.copy2(src, dest)
        os.chmod(dest, 0o755)
        signer = self._find_binary_sign_tool()
        if signer:
            tmp = dest + ".signed"
            result = subprocess.run(
                [signer, "sign", "-inFile", dest, "-outFile", tmp,
                 "-selfSign", "1"],
                capture_output=True, text=True,
            )
            if result.returncode == 0 and os.path.isfile(tmp):
                os.replace(tmp, dest)
                os.chmod(dest, 0o755)
        return marker_dir

    def _prepare_runtime_libs(self):
        """Download & unpack cargo's runtime shared libraries; return lib dirs."""
        base = os.path.join(self.build_folder, "rust-runtime")
        os.makedirs(base, exist_ok=True)
        lib_dirs = []
        for name, url, sha256 in RUST_RUNTIME_BOTTLES:
            tgz = os.path.join(base, name + ".tar.gz")
            if not os.path.isfile(tgz):
                try:
                    download(self, url, tgz, sha256=sha256)
                except Exception as e:
                    # 明确报因：这是外部 CDN 制品，版本会轮换；失败时不要让它以
                    # 深层栈的形式出现，直接给出可执行的排查方向
                    raise ConanException(
                        "cargo runtime library bottle unavailable: %s\n"
                        "  cargo's DT_NEEDED requires libssl.so/libcrypto.so and "
                        "the OHOS image cannot replace them "
                        "(no SSL_get0_group_name in the system OpenSSL 3.x; "
                        "registry openssl/3.5.8.1 is static-only).\n"
                        "  Check the URL/revision is still published "
                        "(harmonybrew revisions rotate) and update "
                        "RUST_RUNTIME_BOTTLES url+sha256 together.\n"
                        "  original error: %s" % (url, e))
            extract_dir = os.path.join(base, name)
            os.makedirs(extract_dir, exist_ok=True)
            with tarfile.open(tgz, "r:gz") as tf:
                tf.extractall(extract_dir)
            for root, _dirs, files in os.walk(extract_dir):
                if os.path.basename(root) != "lib":
                    continue
                # 只需 libssl/libcrypto：cargo 的 DT_NEEDED 虽含 libz.so，
                # 但由系统 /usr/lib/libz.so.1 满足（无需第三方 zlib）
                if any(f.startswith(("libssl.", "libcrypto.")) for f in files):
                    lib_dirs.append(root)
        return lib_dirs

    def _ca_bundle(self):
        candidates = [
            os.environ.get("CURL_CA_BUNDLE"),
            os.environ.get("SSL_CERT_FILE"),
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
            os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _configure_rsproxy(self, cargo_home, ca_bundle=None):
        os.makedirs(cargo_home, exist_ok=True)
        config_path = os.path.join(cargo_home, "config.toml")
        content = (
            "[source.crates-io]\n"
            "replace-with = \"rsproxy-sparse\"\n\n"
            "[source.rsproxy-sparse]\n"
            "registry = \"sparse+https://rsproxy.cn/index/\"\n\n"
            "[net]\n"
            "git-fetch-with-cli = true\n"
            "retry = 3\n"
        )
        if ca_bundle:
            content += ("\n[http]\n"
                        "cainfo = \"%s\"\n" % ca_bundle)
        with open(config_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)

    # ── packaging ──────────────────────────────────────────────────────

    def package(self):
        copy(self, BINARY_NAME, src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "res"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
