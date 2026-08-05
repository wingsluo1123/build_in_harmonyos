#!/usr/bin/env python3
"""Conan 2.x recipe — apko 1.2.17 (Chainguard).

apko is a tool that builds OCI container images from APK packages
directly, without Docker. It is a pure-Go static binary
(CGO_ENABLED=0).

Platform notes:
- E128 (Go binaries require ELF signing): every ELF that is to be
  execve'd on HongMeng must carry a .codesign section. This applies
  to the produced apko binary and the Go toolchain itself. We
  self-bootstrap a portable Go tarball and re-sign every toolchain
  ELF with binary-sign-tool.
- E166 (Go linker mmap fails on HMDFS): routed around by pointing
  GOCACHE/GOTMPDIR and the linker -o output at the ext2 partition.
- E077 (ELF signing + chmod semantics on HMDFS): after signing,
  chmod 0o755 restores the owner x bit.
"""
import hashlib
import os
import shutil
import tarfile

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.errors import ConanException


# Pre-installed, ELF-signed Go toolchain on the HarmonyOS PC preflight
# worker (present on some workers; nuclei/argo/kubo used this path).
_SDK_GO_CANDIDATES = [
    "/storage/Users/currentUser/sdk/go1.26.3/bin/go",
    "/storage/Users/currentUser/sdk/go1.26.3/go/bin/go",
    "/storage/Users/currentUser/sdk/go1.25.7/bin/go",
    "/storage/Users/currentUser/sdk/go1.25.7/go/bin/go",
    "/storage/Users/currentUser/sdk/go/bin/go",
]

# Portable Go toolchain for self-bootstrapping. apko go.mod requires
# go 1.26.0; Go 1.26.3 satisfies it.
_GO_TARBALL_URLS = [
    "https://golang.google.cn/dl/go1.26.3.linux-arm64.tar.gz",
    "https://dl.google.com/go/go1.26.3.linux-arm64.tar.gz",
]
_GO_TARBALL_SHA256 = "9d89a3ea57d141c2b22d70083f2c8459ba3890f2d9e818e7e933b75614936565"
_GO_VERSION = "1.26.3"

# ELF signing tools on the HarmonyOS PC preflight worker.
_OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"
_SIGNTOOL = "/data/service/hnp/bin/binary-sign-tool"

# ext2 partition paths that bypass HMDFS mmap restrictions (E166).
_EXT2_CACHE_CANDIDATES = [
    "/data/storage/el2/base/haps/entry/files",
    "/data/storage/el2/base/cache",
]


class ApkoConan(ConanFile):
    name = "apko"
    version = "1.2.17"
    description = "Build OCI images from APK packages directly"
    license = "Apache-2.0"
    homepage = "https://github.com/chainguard-dev/apko"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # Go toolchain resolution
    # ------------------------------------------------------------------
    def _ensure_go(self):
        """Locate or self-bootstrap a signed, executable go."""
        existing = shutil.which("go")
        if existing and os.access(existing, os.X_OK):
            self.output.info("Using Go from PATH: %s" % existing)
            return existing

        for cand in _SDK_GO_CANDIDATES:
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                self.output.info("Using SDK Go: %s" % cand)
                return cand
            if os.path.isfile(cand):
                self.output.warning(
                    "SDK Go found at %s but not executable (E128 signature?"
                    "); continuing probe" % cand
                )

        self.output.info(
            "No signed SDK Go on PATH or under ~/sdk/; self-bootstrapping Go %s "
            "and re-signing toolchain ELFs (E128+E077 workaround)" % _GO_VERSION
        )
        return self._bootstrap_go()

    def _bootstrap_go(self):
        """Download, verify, extract and re-sign a portable Go toolchain."""
        ext2 = self._ext2_cache_dir()
        boot_root = os.path.join(ext2, "go-bootstrap", "go%s" % _GO_VERSION)
        go_bin = os.path.join(boot_root, "bin", "go")
        marker = os.path.join(boot_root, ".hmbs-signed-ok")

        if os.path.isfile(marker) and os.path.isfile(go_bin):
            self.output.info("Reusing cached signed Go bootstrap: %s" % go_bin)
            return go_bin

        import urllib.request
        import ssl

        bootstrap_parent = os.path.dirname(boot_root)
        os.makedirs(bootstrap_parent, exist_ok=True)
        shipped_root = os.path.join(bootstrap_parent, "go")
        if os.path.isdir(shipped_root):
            shutil.rmtree(shipped_root, ignore_errors=True)
        if os.path.isdir(boot_root):
            shutil.rmtree(boot_root, ignore_errors=True)

        tarball_path = os.path.join(bootstrap_parent, "go%s.tar.gz" % _GO_VERSION)
        last_err = None
        for url in _GO_TARBALL_URLS:
            try:
                self.output.info("Downloading Go %s from %s" % (_GO_VERSION, url))
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urllib.request.urlopen(url, timeout=120, context=ctx) as r, \
                        open(tarball_path, "wb") as out:
                    shutil.copyfileobj(r, out)
                last_err = None
                break
            except Exception as e:
                last_err = e
                self.output.warning("Download from %s failed: %s" % (url, e))
                continue
        if last_err is not None:
            raise ConanException(
                "Could not download Go %s from any mirror: %s. URLs tried: %s"
                % (_GO_VERSION, last_err, _GO_TARBALL_URLS)
            )

        actual_sha = hashlib.sha256(open(tarball_path, "rb").read()).hexdigest()
        if actual_sha != _GO_TARBALL_SHA256:
            raise ConanException(
                "Go tarball SHA-256 mismatch: expected %s, got %s (URL %s)"
                % (_GO_TARBALL_SHA256, actual_sha, url)
            )
        self.output.info("Go tarball SHA-256 verified: %s" % actual_sha)

        with tarfile.open(tarball_path, "r:gz") as tf:
            tf.extractall(bootstrap_parent)
        try:
            os.remove(tarball_path)
        except OSError:
            pass
        if not os.path.isdir(shipped_root):
            raise ConanException(
                "Go tarball extracted but %s missing" % shipped_root
            )
        os.rename(shipped_root, boot_root)

        self._sign_go_toolchain(boot_root)

        with open(marker, "w") as f:
            f.write("signed go %s\n" % _GO_VERSION)
        self.output.info("Self-bootstrapped Go ready: %s" % go_bin)
        return go_bin

    def _sign_elf(self, target):
        """Sign one ELF in place for HongMeng execve (E077 four-step)."""
        if not os.path.isfile(target):
            return False
        import subprocess
        self.run(
            "%s --remove-section .codesign %s" % (_OBJCOPY, target),
            env=None, quiet=True, stderr=subprocess.DEVNULL,
        )
        rc = self.run(
            "%s sign -inFile %s -outFile %s -selfSign 1"
            % (_SIGNTOOL, target, target),
            env=None, quiet=True, stderr=subprocess.DEVNULL,
        )
        if rc != 0:
            return False
        try:
            os.chmod(target, 0o755)
        except OSError:
            pass
        return os.access(target, os.X_OK)

    def _sign_go_toolchain(self, boot_root):
        """Re-sign every executable ELF in a freshly extracted Go tree."""
        tool_subdir = os.path.join(boot_root, "pkg", "tool", "linux_arm64")
        targets = []
        for d in (os.path.join(boot_root, "bin"), tool_subdir):
            if not os.path.isdir(d):
                continue
            for name in os.listdir(d):
                p = os.path.join(d, name)
                if os.path.isfile(p):
                    targets.append(p)

        signed, failed = 0, 0
        for t in targets:
            ok = self._sign_elf(t)
            if ok:
                signed += 1
            else:
                failed += 1
                self.output.warning(
                    "Failed to sign Go toolchain ELF %s (E128 may follow)" % t
                )
        self.output.info(
            "Signed %d Go toolchain ELFs (%d failed) under %s"
            % (signed, failed, boot_root)
        )
        if failed:
            raise ConanException(
                "Go toolchain ELF signing failed for %d files under %s"
                % (failed, boot_root)
            )

    def _ext2_cache_dir(self):
        """Pick a writable ext2 directory for GOCACHE/GOTMPDIR/linker output."""
        for base in _EXT2_CACHE_CANDIDATES:
            candidate = os.path.join(base, "apko-1.2.17")
            try:
                os.makedirs(candidate, exist_ok=True)
                with open(os.path.join(candidate, ".wprobe"), "wb") as f:
                    f.write(b"0")
                os.remove(os.path.join(candidate, ".wprobe"))
                self.output.info("Using ext2 cache dir: %s" % candidate)
                return candidate
            except OSError:
                continue
        fallback = os.environ.get("TMPDIR") or os.environ.get("TEMP") or "/tmp"
        self.output.warning(
            "No writable ext2 cache dir found; falling back to %s "
            "(E166 linker-mmap failure may follow)" % fallback
        )
        return fallback

    def _go_env(self):
        """Build the Go environment for the HarmonyOS PC preflight worker."""
        go_bin = self._ensure_go()
        go_bin_dir = os.path.dirname(go_bin)
        go_root = os.path.dirname(go_bin_dir)
        ext2_cache = self._ext2_cache_dir()

        gopath = os.path.join(ext2_cache, "gopath")
        gocache = os.path.join(ext2_cache, "go-cache")
        gotmpdir = os.path.join(ext2_cache, "go-tmp")
        os.makedirs(gopath, exist_ok=True)
        os.makedirs(gocache, exist_ok=True)
        os.makedirs(gotmpdir, exist_ok=True)

        env = {
            "CGO_ENABLED": "0",
            "GOPROXY": "https://goproxy.cn,direct",
            "GOFLAGS": "-mod=mod",
            "GOTOOLCHAIN": "local",
            "GOROOT": go_root,
            "GOPATH": gopath,
            "GOCACHE": gocache,
            "GOTMPDIR": gotmpdir,
            "TMPDIR": gotmpdir,
            "TEMP": gotmpdir,
            "PATH": "%s%s%s" % (go_bin_dir, os.pathsep, os.environ.get("PATH", "")),
        }
        return env, go_bin

    def _run_go(self, cmd, env, cwd):
        """Run a Go command with the env dict actually applied."""
        saved = {}
        for k, v in env.items():
            saved[k] = os.environ.get(k)
            os.environ[k] = v
        try:
            return self.run(cmd, env=None, cwd=cwd)
        finally:
            for k, old in saved.items():
                if old is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = old

    def build(self):
        apply_conandata_patches(self)
        env, go_bin = self._go_env()

        ext2_out = os.path.join(self._ext2_cache_dir(), "apko-bin")
        build_out = os.path.join(self.build_folder, "apko")

        src = self.source_folder

        # Sanity-probe the resolved go
        self._run_go("%s version" % go_bin, env, cwd=src)

        # Pre-download all modules
        self._run_go("%s mod download" % go_bin, env, cwd=src)

        # Build the apko binary (static, stripped) with version info
        git_version = "1.2.17"
        git_hash = "unknown"
        git_treestate = "clean"
        build_date = "2026-08-05"
        pkg = "sigs.k8s.io/release-utils/version"
        ldflags = (
            "-buildid= "
            "-X %s.gitVersion=%s "
            "-X %s.gitCommit=%s "
            "-X %s.gitTreeState=%s "
            "-X %s.buildDate=%s"
            % (pkg, git_version, pkg, git_hash, pkg, git_treestate, pkg, build_date)
        )

        self._run_go(
            "%s build -trimpath -ldflags='%s' -o %s ./"
            % (go_bin, ldflags, ext2_out),
            env,
            cwd=src,
        )
        if not os.path.isfile(ext2_out):
            raise ConanException(
                "go build did not produce %s (E166 linker-mmap failure?)" % ext2_out
            )
        # Sign the produced apko ELF for HongMeng execve (E128)
        if not self._sign_elf(ext2_out):
            raise ConanException(
                "ELF signing of %s failed — apko will not execve on HongMeng"
                % ext2_out
            )
        shutil.copy2(ext2_out, build_out)

    def package(self):
        copy(self, "apko", self.build_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
