#!/usr/bin/env python3
"""Conan recipe — kakoune-lsp 21.0.2 (cargo)

kakoune-lsp (binary name ``kak-lsp``) is a Language Server Protocol client
for the Kakoune editor, written in Rust (kakoune-lsp/kakoune-lsp,
Unlicense/MIT). Single-crate CLI with no default features: the only
feature ``crash-reporting`` pulls ``sentry`` (which drags openssl-sys
through native-tls) and is NOT enabled — the default build is a pure Rust
dependency set with zero C-library link requirements.

OHOS adaptation (0 source patches):
- Toolchain handling follows archives/b/below/0.11.0 (merged):
  tool_requires the rust-toolchain/1.97.1 infra package (rust-lang
  official dist, host & target both aarch64-unknown-linux-ohos). The
  package binaries carry no OHOS code signature, so cargo/rustc (and
  the librustc_driver dylib rustc dlopens) are copied into the build
  folder and self-signed with binary-sign-tool; the read-only payload
  (rustlib/ etc.) is symlinked.
- cargo's runtime shared libraries (NEEDED libssl.so/libcrypto.so/
  libz.so, unversioned sonames; the OHOS loader ignores DT_RUNPATH)
  are synthesized from the conan openssl/3.5.6.1.1 static archives
  (clang -shared --whole-archive, cbindgen/0.28.0 precedent) plus the
  system libz; the Harmonybrew bottle URLs previously used are
  region-flaky (HTTP 404 on CI workers while 200 locally, CI #91538)
  and are no longer used. The synthesized directory goes on
  LD_LIBRARY_PATH for the cargo/rustc processes only.
- A system cargo/rustc is used directly when present (fast path on
  dev machines).
- .cargo/config.toml: clang linker for the aarch64-unknown-linux-ohos
  target + rsproxy.cn sparse mirror + network tolerance
  (multiplexing=false — device libcurl lacks HTTP/2).
- Upstream tests (16 #[test] across markup/position/text_edit/util)
  run in build() (below/0.11.0 precedent; MANIFEST declares
  upstream_test_in_build: true — the CI worker has no cargo during
  the test_package phase). The test_package phase runs the consumer
  smoke cases against the packaged (signed) bin/kak-lsp.
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class KakouneLspConan(ConanFile):
    name = "kakoune-lsp"
    version = "21.0.2"
    description = "Kakoune Language Server Protocol Client"
    license = "Unlicense/MIT"
    homepage = "https://github.com/kakoune-lsp/kakoune-lsp"
    url = "https://github.com/kakoune-lsp/kakoune-lsp"
    topics = ("lsp", "kakoune", "rust", "language-server-protocol")

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        # R32: settings.os check must use in (Linux, OHOS)
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kakoune-lsp supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        # Rust 工具链由制品仓基础设施包提供（适配令前置确认已发布）：
        # rust-lang 官方 dist 预编译 tarball，宿主与目标均为
        # aarch64-unknown-linux-ohos，可直接在 HarmonyOS 上执行（签名
        # 处理见 _prepare_signed_toolchain）。不使用 rustup 引导——标准
        # rustup 无法识别 HarmonyOS 宿主（E105/E154）。
        self.tool_requires("rust-toolchain/1.97.1")
        # cargo 运行期 libssl/libcrypto 的静态归档来源（合成见
        # _synthesize_runtime_libs）。Harmonybrew bottle URL 区域不稳
        # （CI worker 404、本机 200，#91538 实测），弃用；cbindgen/
        # 0.28.0 先例。
        self.tool_requires("openssl/3.5.6.1.1")

    # ------------------------------------------------------------------
    # .cargo/config.toml: clang linker + rsproxy.cn sparse mirror + 网络容错
    # ------------------------------------------------------------------
    def _cargo_config_content(self):
        # 与 alacritty/0.17.0、argc/1.24.0 一致：
        # (1) multiplexing=false——设备 cargo 链接的 libcurl 可能未编译
        #     HTTP/2，sparse 索引默认多路复用直接报
        #     "failed to enable HTTP/2, is curl not built right?"，
        #     强制 HTTP/1.1 后 rsproxy.cn sparse 正常；
        # (2) cainfo 指向存在的系统 CA 存储（设备无默认 CA bundle）。
        content = '[build]\ntarget-dir = "target"\n'
        if str(self.settings.os) == "OHOS":
            content += (
                "\n[target.aarch64-unknown-linux-ohos]\n"
                'linker = "/data/service/hnp/bin/clang"\n'
            )
        content += (
            "\n[source.crates-io]\n"
            'replace-with = "rsproxy-sparse"\n'
            "\n[source.rsproxy-sparse]\n"
            'registry = "sparse+https://rsproxy.cn/index/"\n'
            "\n[net]\n"
            "retry = 10\n"
            "\n[http]\n"
            "timeout = 600\n"
            "low-speed-limit = 1\n"
            "multiplexing = false\n"
        )
        for ca in self._ca_candidates():
            if os.path.isfile(ca):
                content += 'cainfo = "%s"\n' % ca
                break
        return content

    @staticmethod
    def _ca_candidates():
        return [
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
            os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem"),
        ]

    def _write_cargo_configs(self):
        """Write .cargo/config.toml into both the source and build folders.

        cargo discovers config.toml from the cwd and its ancestors; build()
        runs with cwd = source folder (where Cargo.toml lives), so the
        config MUST exist there (libsignal-core 0.103.1 CI #63478
        precedent). The build folder copy is kept for conan-layout
        compatibility.
        """
        content = self._cargo_config_content()
        for base in (self.source_folder, self.build_folder):
            cargo_dir = os.path.join(base, ".cargo")
            os.makedirs(cargo_dir, exist_ok=True)
            with open(os.path.join(cargo_dir, "config.toml"), "w") as f:
                f.write(content)

    # ------------------------------------------------------------------
    # Toolchain discovery / signing / runtime libs
    # ------------------------------------------------------------------
    @staticmethod
    def _find_cargo():
        """Probe well-known OHOS locations for the cargo binary.

        Harmonybrew installs may ship ``bin/cargo`` as a wrapper script
        that execs ``cargo.real`` at a Cellar absolute path; prefer a
        ``.real`` sibling so the real binary is executed."""
        candidates = [
            shutil.which("cargo"),
            "/storage/Users/currentUser/.harmonybrew/bin/cargo",
            "/storage/Users/currentUser/.cargo/bin/cargo",
            os.path.expanduser("~/.harmonybrew/bin/cargo"),
            os.path.expanduser("~/.cargo/bin/cargo"),
            "/data/service/hnp/bin/cargo",
            "/storage/Users/currentUser/usr/local/bin/cargo",
        ]
        for cand in candidates:
            if not cand:
                continue
            if not cand.endswith(".real") and os.path.isfile(cand + ".real"):
                cand = cand + ".real"
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        return None

    def _find_binary_sign_tool(self):
        """Locate the OHOS binary signing tool (below/0.11.0 precedent)."""
        candidates = [
            os.environ.get("BINARY_SIGN_TOOL"),
            shutil.which("binary-sign-tool"),
            "/data/service/hnp/bin/binary-sign-tool",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _rust_toolchain_dep(self):
        """Return the rust-toolchain tool_requires dependency (or None)."""
        try:
            return self.dependencies.build.get("rust-toolchain")
        except (KeyError, ConanException):
            return None

    def _toolchain_dir(self):
        return os.path.join(self.build_folder, "rust-toolchain")

    def _prepare_signed_toolchain(self):
        """Prepare an executable Rust toolchain; return its bin dir.

        rust-toolchain/1.97.1 ships the rust-lang official dist tarball;
        its binaries carry no OHOS code signature and OHOS refuses to
        execve unsigned ELFs (EACCES). cargo/rustc and the
        librustc_driver dylib rustc dlopens are copied into the build
        folder and self-signed; the read-only payload (rustlib/ etc.)
        is symlinked — below/0.11.0 precedent. Idempotent via marker.
        """
        dst = self._toolchain_dir()
        bin_dst = os.path.join(dst, "bin")
        lib_dst = os.path.join(dst, "lib")
        marker = os.path.join(dst, ".prepared")
        if os.path.isfile(marker):
            return bin_dst
        tool = self._rust_toolchain_dep()
        if not tool:
            raise ConanInvalidConfiguration(
                "rust-toolchain/1.97.1 tool_requires package not available"
            )
        src = tool.package_folder
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)

        signer = self._find_binary_sign_tool()
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool not found; OHOS rejects unsigned ELFs"
            )

        to_sign = []
        for name in ("cargo", "rustc"):
            src_bin = os.path.join(src, "bin", name)
            if os.path.isfile(src_bin):
                dst_bin = os.path.join(bin_dst, name)
                if not os.path.isfile(dst_bin):
                    shutil.copy2(src_bin, dst_bin)
                    os.chmod(dst_bin, 0o755)
                to_sign.append(dst_bin)
        src_lib = os.path.join(src, "lib")
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                if name.startswith("librustc_driver") and name.endswith(".so"):
                    dst_lib = os.path.join(lib_dst, name)
                    if not os.path.isfile(dst_lib):
                        shutil.copy2(os.path.join(src_lib, name), dst_lib)
                        os.chmod(dst_lib, 0o755)
                    to_sign.append(dst_lib)

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
                    % (path, result.returncode, (result.stderr or "")[:200])
                )
            os.replace(tmp, path)
            os.chmod(path, 0o755)
            self.output.info(
                "signed toolchain binary: %s" % os.path.basename(path))

        # Read-only payload: symlink (rustc's sysroot must stay visible).
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                dst_lib = os.path.join(lib_dst, name)
                if not os.path.exists(dst_lib):
                    os.symlink(os.path.join(src_lib, name), dst_lib)
        for name in ("etc", "libexec", "share"):
            src_dir = os.path.join(src, name)
            dst_dir = os.path.join(dst, name)
            if os.path.isdir(src_dir) and not os.path.exists(dst_dir):
                os.symlink(src_dir, dst_dir)

        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("signed toolchain prepared\n")
        return bin_dst

    def _synthesize_runtime_libs(self):
        """Synthesize the cargo runtime shared libraries (cbindgen/0.28.0
        precedent) and return their directory.

        cargo NEEDED libssl.so/libcrypto.so/libz.so (unversioned sonames;
        the OHOS loader ignores DT_RUNPATH). The conan openssl package
        ships static archives only, so shared objects with the right
        sonames are linked from them (clang -shared --whole-archive);
        libz comes from the system zlib (the conan zlib static archive
        is not PIC). The Harmonybrew bottle URLs previously used here
        are region-flaky (HTTP 404 on CI workers while 200 locally,
        CI #91538) and are no longer used.
        """
        runtime = os.path.join(self.build_folder, "cargo-runtime")
        os.makedirs(runtime, exist_ok=True)
        openssl = self.dependencies.build["openssl"]
        arch_dir = None
        for d in openssl.cpp_info.libdirs:
            arch_dir = d if os.path.isabs(d) else os.path.join(
                openssl.package_folder, d)
            break
        if not arch_dir or not os.path.isfile(
                os.path.join(arch_dir, "libcrypto.a")):
            raise ConanInvalidConfiguration(
                "openssl static archives not found in openssl/3.5.6.1.1"
            )
        cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        crypto = os.path.join(runtime, "libcrypto.so")
        ssl = os.path.join(runtime, "libssl.so")
        if not os.path.isfile(crypto):
            subprocess.check_call(
                [cc, "-shared", "-Wl,-z,relro,-z,now",
                 "-Wl,-soname,libcrypto.so", "-Wl,--whole-archive",
                 os.path.join(arch_dir, "libcrypto.a"),
                 "-Wl,--no-whole-archive", "-ldl", "-pthread", "-o", crypto])
        if not os.path.isfile(ssl):
            subprocess.check_call(
                [cc, "-shared", "-Wl,-z,relro,-z,now",
                 "-Wl,-soname,libssl.so", "-Wl,--whole-archive",
                 os.path.join(arch_dir, "libssl.a"),
                 "-Wl,--no-whole-archive", "-L" + runtime, "-lcrypto",
                 "-ldl", "-pthread", "-o", ssl])
        libz = os.path.join(runtime, "libz.so")
        if not os.path.lexists(libz):
            linked = False
            for z in ("/usr/lib/libz.so.1", "/system/lib64/libz.so.1",
                      "/usr/lib/libz.so"):
                if os.path.exists(z):
                    os.symlink(z, libz)
                    linked = True
                    break
            if not linked:
                raise ConanInvalidConfiguration(
                    "no system libz found for the cargo runtime"
                )
        self.output.info("cargo runtime libs synthesized at %s" % runtime)
        return runtime

    def _ensure_toolchain(self):
        """Return (cargo_path, lib_dirs).

        Fast path: a system cargo/rustc (local dev machines) is used
        directly with no extra lib dirs. CI workers have none — the
        toolchain then comes from the rust-toolchain/1.97.1 infra
        package (signed copy via _prepare_signed_toolchain); lib_dirs
        covers the toolchain lib dir (librustc_driver for rustc) and
        the synthesized cargo runtime libs (libssl/libcrypto/libz).
        """
        cargo = self._find_cargo()
        if cargo:
            return cargo, []
        bin_dir = self._prepare_signed_toolchain()
        cargo = os.path.join(bin_dir, "cargo")
        if not os.path.isfile(cargo):
            raise ConanInvalidConfiguration(
                "cargo not found in prepared rust-toolchain"
            )
        runtime = self._synthesize_runtime_libs()
        return cargo, [os.path.join(self._toolchain_dir(), "lib"), runtime]

    def _build_env(self, cargo, lib_dirs):
        """Build env: clang as the C linker for cargo build scripts, a
        writable TMPDIR (OHOS /tmp is read-only), a CA bundle for
        cargo's TLS, the toolchain bin dir first on PATH (so cargo
        invokes the matching rustc), and the cargo runtime shared
        libraries on LD_LIBRARY_PATH (OHOS loader ignores DT_RUNPATH)."""
        env = dict(os.environ)
        if lib_dirs:
            prev = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = ":".join(
                lib_dirs + ([prev] if prev else [])
            )
        env["PATH"] = (
            os.path.dirname(cargo) + os.pathsep + env.get("PATH", "")
        )
        clang = shutil.which("clang") or "/data/service/hnp/bin/clang"
        clangxx = shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        env["CC"] = clang
        env["CXX"] = clangxx
        env.setdefault("CFLAGS", "-fPIC -O2")
        env.setdefault("CXXFLAGS", "-fPIC -O2")
        env["RUSTFLAGS"] = f"-C linker={clang}"
        tmpdir = os.environ.get("HMBS_TMPDIR") or os.environ.get("TMPDIR")
        if not tmpdir:
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp", "kakoune-lsp")
            os.makedirs(tmpdir, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP"):
            env[var] = tmpdir
        hnp_bin = "/data/service/hnp/bin"
        if os.path.isdir(hnp_bin):
            env["PATH"] = hnp_bin + os.pathsep + env.get("PATH", "")
        if not env.get("SSL_CERT_FILE"):
            for ca in self._ca_candidates():
                if os.path.isfile(ca):
                    env["SSL_CERT_FILE"] = ca
                    env["CURL_CA_BUNDLE"] = ca
                    break
        return env

    # ------------------------------------------------------------------
    # build + upstream tests (below/0.11.0 precedent)
    # ------------------------------------------------------------------
    def _run_upstream_tests(self, cargo, env):
        """Run the upstream cargo test suite in build().

        below/0.11.0 precedent — the MANIFEST declares
        upstream_test_in_build: true because the CI worker has no cargo
        during the test_package phase. 16 registered #[test] across
        markup/position/text_edit/util; --tests excludes the doc-tests
        phase (no usable rustdoc in the OHOS Rust toolchain,
        alacritty/0.17.0 precedent; kakoune-lsp has no doctest blocks,
        0 cases affected). Fails the build on any test failure or a
        registration mismatch.
        """
        cmd = [cargo, "test", "--release", "--locked", "-j", "2", "--tests"]
        self.output.info("running upstream tests: %s" % " ".join(cmd[1:]))
        proc = subprocess.run(
            cmd, cwd=self.source_folder, env=env,
            capture_output=True, text=True, timeout=3600,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        print(output, flush=True)

        result_lines = re.findall(
            r"test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored",
            output,
        )
        passed = sum(int(n) for _, n, _, _ in result_lines)
        failed = sum(int(n) for _, _, n, _ in result_lines)
        filtered = 0
        for m in re.finditer(r"(\d+) filtered out", output):
            filtered = max(filtered, int(m.group(1)))
        executed = passed + failed
        total = executed + filtered
        marker = {
            "status": "passed" if (proc.returncode == 0 and failed == 0
                                   and executed > 0) else "failed",
            "framework": "cargo",
            "command": "cargo test --release --locked --tests",
            "discovered": total,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": filtered,
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker,
                                                       ensure_ascii=False))
        if total != 16:
            raise ConanInvalidConfiguration(
                "upstream test registration mismatch: expected 16, got "
                "executed=%d + filtered=%d (verdict lines: %s)"
                % (executed, filtered, result_lines)
            )
        if failed > 0 or proc.returncode != 0:
            raise ConanInvalidConfiguration(
                "upstream cargo test failed (rc=%d, failed=%d)"
                % (proc.returncode, failed)
            )

    def build(self):
        self._write_cargo_configs()
        cargo, lib_dirs = self._ensure_toolchain()
        env = self._build_env(cargo, lib_dirs)
        self.output.info("building kak-lsp with cargo: %s" % cargo)
        # 上游 Cargo.lock 与 manifest 完全匹配（sha256 与 tag 归档一致），
        # --locked 保证零重解析、版本零漂移。-j 2：HMFS 上并发链接偶发
        # "Text file busy (os error 26)"，限并发规避（alacritty 先例）。
        # 默认 feature 集为空（唯一 feature crash-reporting 拉 sentry/
        # openssl-sys，不启用）——纯 Rust 依赖集，零 C 库链接需求。
        subprocess.check_call(
            [cargo, "build", "--release", "--locked", "-j", "2"],
            cwd=self.source_folder,
            env=env,
        )
        self._run_upstream_tests(cargo, env)

    @staticmethod
    def _sign_elf(path):
        """OHOS ELF codesign (kysdk-desktop 3.0.1.0 / wlopm 1.0.0
        precedent) — unconditional re-sign so the packaged binary is
        executable by the test_package phase on any worker."""
        signer = shutil.which("binary-sign-tool") or \
            "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration("binary-sign-tool not found")
        tmp = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", tmp,
             "-selfSign", "1"], check=True, timeout=60)
        os.chmod(tmp, 0o755)
        os.replace(tmp, path)

    def package(self):
        # target-dir resolves relative to the cargo invocation cwd
        # (source folder); probe the build-folder variant as well
        # (libsignal-core 0.103.1 layout precedent).
        target_dir = os.path.join(self.source_folder, "target", "release")
        if not os.path.isfile(os.path.join(target_dir, "kak-lsp")):
            target_dir = os.path.join(self.build_folder, "target", "release")
        if not os.path.isfile(os.path.join(target_dir, "kak-lsp")):
            raise ConanInvalidConfiguration(
                "cargo build produced no kak-lsp binary under %s" % target_dir
            )
        dst = os.path.join(self.package_folder, "bin")
        copy(self, "kak-lsp", src=target_dir, dst=dst)
        self._sign_elf(os.path.join(dst, "kak-lsp"))
        copy(self, "UNLICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
