#!/usr/bin/env python3
"""Conan 2.x recipe — zrok 2.0.4 (Go CLI)

zrok is a next-generation peer-to-peer sharing platform from openziti
(https://zrok.io / https://github.com/openziti/zrok).  This recipe builds the
main `zrok2` CLI (module github.com/openziti/zrok/v2, upstream `make build`
target).

Key adaptation points for OHOS (aarch64-linux-ohos):

* zrok depends on github.com/mattn/go-sqlite3, which is a cgo-only package
  (`//go:build cgo`).  With CGO_ENABLED=0 the package becomes empty and
  `controller/createFrontend.go` fails with `undefined: sqlite3.Error`.
  Upstream itself builds with CGO_ENABLED=1 (`.goreleaser-linux-arm64.yml`
  sets `CC=aarch64-linux-gnu-gcc`).  On OHOS we use the OHOS SDK clang
  `aarch64-unknown-linux-ohos-clang`, which produces a proper
  ld-musl-aarch64 native ELF (static-cgo-free, signed via binary-sign-tool).
* The web UI (`ui/` and `agent/agentUi/`) is skipped with the upstream-provided
  `-tags no_zrok_ui` build tag: upstream ships `embed_stub.go` files behind
  that tag so the `//go:embed dist` placeholder is not required.  The npm
  frontend build is intentionally bypassed (headless CLI).
* Go linker output is routed into a writable ext2 go-workspace
  (`/data/storage/el2/base/haps/entry/files/...`, overridable via
  OHOS_GO_WORKDIR) because HMDFS rejects the linker's mmap of output files
  (E124/E134/E166).  GOCACHE/GOMODCACHE/GOTMPDIR live there too.
* Every produced/test ELF is self-signed with binary-sign-tool
  (SHA256withECDSA) so it can be execve'd on HarmonyOS.
* Upstream tests: 12 packages carry *_test.go; each is compiled with
  `go test -mod=mod -c -tags no_zrok_ui`, signed, then run from its source
  directory with `-test.v -test.count=1` (E318 pattern).  4 integration tests
  in sdk/golang/sdk self-skip without ZROK2_API_ENDPOINT/ZROK2_ADMIN_TOKEN.
"""
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ZrokConan(ConanFile):
    name = "zrok"
    version = "2.0.4"
    description = "zrok is a next-generation sharing platform for secure, private network and file sharing"
    license = "Apache-2.0"
    homepage = "https://zrok.io/"
    url = "https://github.com/openziti/zrok"
    topics = ("sharing", "p2p", "tunnel", "cli", "go")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # go.mod declares `go 1.26`; the bootstrapped SDK 1.26.0 satisfies it.
    _go_version = "1.26.0"
    _go_archives = {
        "amd64": (
            [
                "https://golang.google.cn/dl/go1.26.0.linux-amd64.tar.gz",
                "https://dl.google.com/go/go1.26.0.linux-amd64.tar.gz",
            ],
            "aac1b08a0fb0c4e0a7c1555beb7b59180b05dfc5a3d62e40e9de90cd42f88235",
        ),
        "arm64": (
            [
                "https://golang.google.cn/dl/go1.26.0.linux-arm64.tar.gz",
                "https://dl.google.com/go/go1.26.0.linux-arm64.tar.gz",
            ],
            "bd03b743eb6eb4193ea3c3fd3956546bf0e3ca5b7076c8226334afe6b75704cd",
        ),
    }
    # Every package with *_test.go files at v2.0.4 (12 packages).  The `go:embed
    # dist` UI packages are excluded via -tags no_zrok_ui (upstream stub).
    _upstream_test_packages = (
        "./cmd/zrok2",
        "./controller",
        "./controller/automation",
        "./controller/limits",
        "./controller/store",
        "./drives/davServer",
        "./drives/davServer/internal/xml",
        "./drives/sync",
        "./endpoints",
        "./endpoints/proxyUi",
        "./sdk/golang/sdk",
        "./util",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("zrok is prepared for Linux/OHOS targets only")

    def generate(self):
        env = Environment()
        env.define("CGO_ENABLED", "1")
        env.define("GOOS", self._goos())
        env.define("GOARCH", self._goarch())
        env.define("GOTOOLCHAIN", "local")
        env.define("GOFLAGS", "-mod=mod")
        env.define("GOPROXY", "https://goproxy.cn,direct")
        env.define("GOSUMDB", "sum.golang.google.cn")

        workspace = self._go_workspace()
        env.define("TMPDIR", os.path.join(workspace, "tmp"))
        env.define("GOTMPDIR", os.path.join(workspace, "tmp"))
        env.define("GOCACHE", os.path.join(workspace, "go-build-cache"))
        env.define("GOMODCACHE", os.path.join(workspace, "go-mod-cache"))

        go = self._go_executable()
        goroot = self._goroot_for_go(go)
        if goroot:
            env.define("GOROOT", goroot)
        env.prepend_path("PATH", os.path.dirname(go))

        cc = self._ohos_cc()
        if cc:
            env.define("CC", cc)
            self._add_llvm_libpath(env)
        env.vars(self).save_script("zrok_go_env")

    def build(self):
        apply_conandata_patches(self)
        go = self._go_executable()
        self._check_go_version(go)

        env = self._go_env_dict(go)

        # No vendor/ upstream: fetch the module closure once through GOPROXY.
        self._subprocess_run(
            [go, "mod", "download"],
            env, self.source_folder,
            os.path.join(self.build_folder, "go-mod-download.log"),
        )

        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        if str(self.settings.os) == "OHOS":
            link_out_dir = os.path.join(self._go_workspace(), "link-out")
        else:
            link_out_dir = out_dir
        os.makedirs(link_out_dir, exist_ok=True)
        linked_exe = os.path.join(link_out_dir, "zrok2")
        final_exe = os.path.join(out_dir, "zrok2")

        # Single-pass build: link into the writable go-workspace (HMDFS mmap
        # restriction, E124/E134/E166), sign, then copy into the package dir.
        self._subprocess_run(
            [
                go, "build", "-trimpath", "-mod=mod", "-tags", "no_zrok_ui",
                "-ldflags", self._go_ldflags(),
                "-o", linked_exe, "./cmd/zrok2",
            ],
            env, self.source_folder,
        )
        self._sign_elf_if_ohos(linked_exe)
        if os.path.abspath(linked_exe) != os.path.abspath(final_exe):
            shutil.copy2(linked_exe, final_exe)

        self._run_upstream_tests(go)

    def package(self):
        copy(self, "zrok2", os.path.join(self.build_folder, "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # --- version injection (upstream .goreleaser parity) ------------------
    @staticmethod
    def _go_ldflags():
        # goreleaser injects build.Version/Hash via -X; replicate with the tag
        # value so `zrok2 version` reports v2.0.4.
        return (
            "-s -w"
            " -X github.com/openziti/zrok/v2/build.Version=v2.0.4"
            " -X github.com/openziti/zrok/v2/build.Hash=2.0.4"
        )

    # --- upstream tests ---------------------------------------------------
    def _run_upstream_tests(self, go):
        env = self._go_env_dict(go)
        log_path = os.path.join(self.build_folder, "upstream-go-test.log")
        if os.path.exists(log_path):
            os.remove(log_path)

        command = "go test -mod=mod -tags no_zrok_ui -c <each pkg> + run signed test binaries -test.v"
        if str(self.settings.os) == "OHOS":
            test_out_dir = os.path.join(self._go_workspace(), "test-out")
            os.makedirs(test_out_dir, exist_ok=True)
            total = {"discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0}
            for package in self._upstream_test_packages:
                safe = self._pkg_safe(package)
                test_bin = os.path.join(test_out_dir, safe + ".test")
                self._subprocess_run(
                    [go, "test", "-mod=mod", "-tags", "no_zrok_ui", "-c", "-o", test_bin, package],
                    env, self.source_folder, log_path,
                )
                self._sign_elf_if_ohos(test_bin)
                pkg_dir = self.source_folder if package == "." else os.path.join(self.source_folder, package[2:])
                pkg_log = os.path.join(test_out_dir, safe + ".log")
                # -test.count=1 disables result caching; run from the package
                # source dir so relative fixtures resolve (E318).
                self._subprocess_run([test_bin, "-test.v", "-test.count=1"], env, pkg_dir, log_path, pkg_log)
                counts = self._parse_go_test_log(pkg_log)
                # P3: per-package floor — a package whose binary exits 0 but
                # yields no parseable test lines must not be silently counted
                # as 0 tests.
                if counts["discovered"] < 1:
                    raise ConanException(
                        "no test results parsed for package %s (log: %s)"
                        % (package, pkg_log)
                    )
                for key in total:
                    total[key] += counts[key]
                print(
                    "HMBS_GO_TEST_PKG=%s discovered=%d passed=%d failed=%d skipped=%d"
                    % (package, counts["discovered"], counts["passed"], counts["failed"], counts["skipped"]),
                    flush=True,
                )
            discovered = total["discovered"]
            executed = discovered
            passed = total["passed"]
            failed = total["failed"]
            skipped = total["skipped"]
        else:
            command = "go test -mod=mod -tags no_zrok_ui -v ./..."
            self._subprocess_run(
                [go, "test", "-mod=mod", "-tags", "no_zrok_ui", "-v", "./..."],
                env, self.source_folder, log_path,
            )
            counts = self._parse_go_test_log(log_path)
            discovered = counts["discovered"]
            executed = counts["executed"]
            passed = counts["passed"]
            failed = counts["failed"]
            skipped = counts["skipped"]

        status = "passed"
        if executed == 0 or failed > 0:
            status = "failed"
        marker = {
            "status": status,
            "framework": "go test",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        print(line, flush=True)
        self.output.info(line)
        if status != "passed":
            raise ConanException("zrok upstream go tests failed: %s" % line)

    @staticmethod
    def _pkg_safe(package):
        if package == ".":
            return "root"
        return package.lstrip("./").replace("/", "_")

    @staticmethod
    def _parse_go_test_log(log_path):
        passed = failed = skipped = 0
        with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped.startswith("--- PASS:"):
                    passed += 1
                elif stripped.startswith("--- FAIL:"):
                    failed += 1
                elif stripped.startswith("--- SKIP:"):
                    skipped += 1
        discovered = passed + failed + skipped
        return {"discovered": discovered, "executed": discovered, "passed": passed, "failed": failed, "skipped": skipped}

    def _subprocess_run(self, args, env, cwd, log_path=None, tee_path=None):
        proc = subprocess.run(args, env=env, cwd=cwd, capture_output=True, text=True)
        output = (proc.stdout or "") + (proc.stderr or "")
        for path in (log_path, tee_path):
            if path:
                with open(path, "a", encoding="utf-8") as handle:
                    handle.write("$ %s\n" % " ".join(args))
                    handle.write(output)
                    if not output.endswith("\n"):
                        handle.write("\n")
        if output:
            print(output, flush=True)
        if proc.returncode != 0:
            raise ConanException(
                "command failed (%s): %s" % (proc.returncode, " ".join(args))
            )

    # --- go toolchain -----------------------------------------------------
    def _go_env_dict(self, go):
        workspace = self._go_workspace()
        env = dict(os.environ)
        env["CGO_ENABLED"] = "1"
        env["GOOS"] = self._goos()
        env["GOARCH"] = self._goarch()
        env["GOTOOLCHAIN"] = "local"
        env["GOFLAGS"] = "-mod=mod"
        env["GOPROXY"] = os.environ.get("GOPROXY", "https://goproxy.cn,direct")
        env["GOSUMDB"] = os.environ.get("GOSUMDB", "sum.golang.google.cn")
        env["TMPDIR"] = os.path.join(workspace, "tmp")
        env["GOTMPDIR"] = os.path.join(workspace, "tmp")
        env["GOCACHE"] = os.path.join(workspace, "go-build-cache")
        env["GOMODCACHE"] = os.path.join(workspace, "go-mod-cache")
        goroot = self._goroot_for_go(go)
        if goroot:
            env["GOROOT"] = goroot
        env["PATH"] = os.path.dirname(go) + os.pathsep + env.get("PATH", "")
        cc = self._ohos_cc()
        if cc:
            env["CC"] = cc
        # OHOS SDK lld needs its bundled libxml2.so.16 (no RUNPATH).
        for lib in self._llvm_lib_dirs():
            env["LD_LIBRARY_PATH"] = lib + os.pathsep + env.get("LD_LIBRARY_PATH", "")
        return env

    def _go_workspace(self):
        if str(self.settings.os) == "OHOS":
            root = os.environ.get(
                "OHOS_GO_WORKDIR",
                "/data/storage/el2/base/haps/entry/files/zrok-conan-go",
            )
        else:
            root = os.path.join(self.build_folder, ".go-work")
        workspace = os.path.join(root, self.version)
        for child in ("tmp", "go-build-cache", "go-mod-cache", "link-out", "test-out", "go-sdk"):
            Path(workspace, child).mkdir(parents=True, exist_ok=True)
        return workspace

    def _ensure_go_toolchain(self):
        host_arch = self._go_host_arch()
        if host_arch not in self._go_archives:
            raise ConanInvalidConfiguration(
                "Go SDK bootstrap is not prepared for host arch: %s" % host_arch
            )
        sdk_root = os.path.join(self._go_workspace(), "go-sdk", "go%s-%s" % (self._go_version, host_arch))
        goroot = os.path.join(sdk_root, "go")
        gobin = os.path.join(goroot, "bin", "go")
        if not os.path.isfile(gobin):
            urls, sha256 = self._go_archives[host_arch]
            self.output.info("Go %s not found; downloading %s" % (self._go_version, urls[0]))
            get(self, url=urls, sha256=sha256, destination=sdk_root, strip_root=False)
        self._sign_go_sdk_if_ohos(goroot)
        return gobin

    def _sign_go_sdk_if_ohos(self, goroot):
        if str(self.settings.os) != "OHOS":
            return
        marker = os.path.join(goroot, ".ohos-signed")
        if os.path.isfile(marker):
            return
        tool_dir = os.path.join(goroot, "pkg", "tool", "linux_%s" % self._go_host_arch())
        candidates = [os.path.join(goroot, "bin", "go"), os.path.join(goroot, "bin", "gofmt")]
        if os.path.isdir(tool_dir):
            candidates.extend(os.path.join(tool_dir, name) for name in os.listdir(tool_dir))
        for candidate in candidates:
            if os.path.isfile(candidate) and self._is_elf(candidate):
                self._sign_elf_if_ohos(candidate)
        Path(marker).write_text("signed\n", encoding="utf-8")

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_elf_if_ohos(self, path):
        if str(self.settings.os) != "OHOS":
            return
        # NOTE: do NOT skip signing when the file already contains
        # `.codesign`/`.note.ohos` bytes: the OHOS lld emits those section
        # NAMES for every linked binary (even unsigned ones), so a naive
        # byte search always matches and would skip the real signature.
        # binary-sign-tool is idempotent (re-signing a signed ELF is safe and
        # cheap), so we always (re-)sign here.
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration("binary-sign-tool is required to sign OHOS Go executables")
        signed = "%s.signed" % path
        subprocess.check_call(
            [signer, "sign", "-selfSign", "1", "-inFile", path,
             "-outFile", signed, "-signAlg", "SHA256withECDSA"]
        )
        shutil.move(signed, path)
        os.chmod(path, 0o755)

    @staticmethod
    def _ohos_cc():
        # cgo needs a C compiler for GOOS=linux GOARCH=arm64; on OHOS the
        # HarmonyOS SDK clang produces a proper ld-musl-aarch64 native ELF.
        candidates = [
            os.environ.get("CC"),
            shutil.which("aarch64-unknown-linux-ohos-clang"),
            "/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    @staticmethod
    def _add_llvm_libpath(env):
        # OHOS SDK lld needs its bundled libxml2.so.16 (no RUNPATH).
        for lib in ZrokConan._llvm_lib_dirs():
            env.prepend_path("LD_LIBRARY_PATH", lib)

    @staticmethod
    def _llvm_lib_dirs():
        candidates = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/toolchains/llvm/lib",
        ]
        return [lib for lib in candidates if os.path.isdir(lib)]

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
            os.path.expanduser("~/sdk/go%s/bin/go" % self._go_version),
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
            output = subprocess.run([go, "version"], capture_output=True, timeout=30).stdout.decode()
        except OSError:
            return False
        match = re.search(r"go(\d+)\.(\d+)", output)
        if not match:
            return False
        required = [int(x) for x in self._go_version.split(".")[:2]]
        current = [int(match.group(1)), int(match.group(2))]
        return current >= required

    def _check_go_version(self, go):
        output = subprocess.check_output([go, "version"], text=True).strip()
        self.output.info(output)
        match = re.search(r"go(\d+)\.(\d+)", output)
        if not match:
            raise ConanInvalidConfiguration("Unable to parse Go version from: %s" % output)
        required = [int(x) for x in self._go_version.split(".")[:2]]
        if [int(match.group(1)), int(match.group(2))] < required:
            raise ConanInvalidConfiguration(
                "zrok 2.0.4 requires Go >= %s (go.mod declares 1.26), got: %s" % (self._go_version, output)
            )

    @staticmethod
    def _goroot_for_go(go):
        resolved = Path(go).resolve()
        goroot = resolved.parent.parent
        if resolved.parent.name == "bin" and (goroot / "pkg").is_dir():
            return str(goroot)
        return None

    @staticmethod
    def _go_host_arch():
        machine = platform.machine().lower()
        return {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
            "armv8l": "arm64",
        }.get(machine, machine)
