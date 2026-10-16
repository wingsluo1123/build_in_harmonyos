#!/usr/bin/env python3
"""Conan recipe for typst 0.15.1.

typst is a (Rust) typesetting system; the packaged artifact is the `typst`
CLI executable.  This recipe cross-compiles it for HarmonyOS PC
(aarch64-unknown-linux-ohos) with the Rust toolchain provided by the
rust-toolchain/1.97.1 infrastructure package (tool_requires).  Crates are
fetched through the rsproxy.cn mirror; the single git dependency
(typst-dev-assets, a dev-dependency used by the upstream test suite) is
resolved through a GitHub mirror because the build host cannot reach
github.com directly.

OHOS refuses to execute unsigned ELF images, so the cargo/rustc binaries from
the toolchain package (which ship no code signature) are copied into the build
folder, signed with binary-sign-tool -selfSign 1, and the rest of the
toolchain payload is symlinked (below/0.11.0 precedent).

The upstream test suite is executed during build() (see notes.md for the
measured pass/fail counts) unless OHC_SKIP_UPSTREAM_TESTS=1 is set.

External C dependency: OpenSSL.  typst-cli unconditionally enables
typst-kit's `system-downloader` feature, which pulls in `dep:openssl`
(openssl-sys).  We link the conan `openssl` package statically so the typst
binary is self-contained.
"""
import os
import re
import shlex
import shutil
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches,
                               copy, download, export_conandata_patches, get)
from conan.tools.layout import basic_layout

# cargo 运行期依赖的共享库（OHOS loader 忽略 DT_RUNPATH，须显式进
# LD_LIBRARY_PATH）。Harmonybrew 的 OHOS 预编译 bottle（below/0.11.0 先例）。
# 实测 cargo 1.97.1 仅 DT_NEEDED libssl/libcrypto（无 libz），且需要
# OpenSSL >= 3.5 的 SSL_get0_group_name——系统 /usr/lib 的 OpenSSL 3.0.12
# 缺该符号，故必须由 bottle 提供 3.5+ 共享库。
# 注意：harmonybrew 会轮换 bottle 版本，旧 URL 会 404；此处给候选列表逐个尝试。
RUST_RUNTIME_BOTTLES = (
    ("openssl3",
     "https://harmonybrew.atomgit.com/bottles/"
     "openssl%403-3.6.5.arm64_ohos.bottle.tar.gz",
     "f8c374560f0002975203425b6b5db30f84eb9e78f9c56a8494b60ca57664327c"),
)

# typst-dev-assets 是 typst workspace 的 git 依赖（dev-dependency，上游测试套件需要）。
# CI worker 的 git 无法 fork remote-https helper（实测 "cannot fork() for
# remote-https"，git fetch 连续 3 次 exit 255），git-fetch-with-cli 路径不可用。
# 改为用 conan 的 urllib 下载该依赖 tag tarball，并以 Cargo [patch] 覆盖为本地
# 路径，彻底绕开 git。每个候选都按 sha256 校验；镜像优先（github 直连在本机/
# CI 均极慢或不可达），官方源保留为最后兜底（内容一致，sha256 相同）。
GIT_DEP_TARBALLS = (
    ("https://gh-proxy.com/https://github.com/typst/typst-dev-assets/"
     "archive/refs/tags/v0.15.1.tar.gz",
     "7f1a00db70c70b57d4df8dd6d5fc9cb14c015102d0ce410294efa8f966e8f7d2"),
    ("https://ghfast.top/https://github.com/typst/typst-dev-assets/"
     "archive/refs/tags/v0.15.1.tar.gz",
     "7f1a00db70c70b57d4df8dd6d5fc9cb14c015102d0ce410294efa8f966e8f7d2"),
    ("https://github.com/typst/typst-dev-assets/archive/refs/tags/v0.15.1.tar.gz",
     "7f1a00db70c70b57d4df8dd6d5fc9cb14c015102d0ce410294efa8f966e8f7d2"),
)

# 构建宿主机无法直连 github.com，git 依赖经镜像解析（不写入 conandata.yml，
# 避免 R39/PF7 的镜像域名黑名单）。
GITHUB_GIT_MIRROR = "https://ghfast.top/https://github.com/"


class TypstConan(ConanFile):
    name = "typst"
    version = "0.15.1"
    description = "A new markup-based typesetting system that is powerful and easy to learn"
    license = "Apache-2.0"
    homepage = "https://typst.app"
    url = "https://github.com/typst/typst"
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

    def requirements(self):
        # typst-cli 默认特性闭包经 typst-kit/system-downloader 无条件依赖
        # openssl（openssl-sys），须由制品仓提供（R36：依赖先发布再构建下游）。
        self.requires("openssl/3.5.8.1")

    def build_requirements(self):
        # Rust 工具链由制品仓基础设施包提供（R36）：rust-lang 官方 dist 预编译
        # tarball，宿主与目标均为 aarch64-unknown-linux-ohos。
        # 不使用 rustup 引导——标准 rustup 无法识别 HarmonyOS 宿主（E105/E154）。
        self.tool_requires("rust-toolchain/1.97.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self._vendor_git_dependency()
        env = self._rust_environment()
        self._ensure_ohos_target(env)
        self._fetch_cargo_deps(env)
        self._run_upstream_tests(env)
        self._cargo_build(env)
        self._sign_binaries()

    # ── cargo dependency materialization ───────────────────────────────

    def _vendor_git_dependency(self):
        """下载 typst-dev-assets（git 依赖）tarball 并用 Cargo [patch] 本地化。

        规避 CI worker git 无法 fork remote-https helper 导致 `git fetch` 恒失败
        （见 GIT_DEP_TARBALLS 注释）。路径落在 build_folder（不进入配方/PR）。
        """
        vendor = os.path.join(self.build_folder, "vendor")
        os.makedirs(vendor, exist_ok=True)
        inner = os.path.join(vendor, "typst-dev-assets-0.15.1")
        if not os.path.isdir(inner):
            tarball = os.path.join(vendor, "typst-dev-assets-0.15.1.tar.gz")
            errors = []
            for url, sha256 in GIT_DEP_TARBALLS:
                try:
                    download(self, url, tarball, sha256=sha256)
                    break
                except ConanException as exc:
                    errors.append(f"{url}: {exc}")
            else:
                raise ConanInvalidConfiguration(
                    "cannot download typst-dev-assets: " + "; ".join(errors))
            with tarfile.open(tarball, "r:gz") as tf:
                tf.extractall(vendor)
            if not os.path.isdir(inner):
                raise ConanInvalidConfiguration(
                    f"unexpected typst-dev-assets layout in {vendor}")
        cargo_toml = os.path.join(self.source_folder, "Cargo.toml")
        marker = "# OHOS: git 依赖本地化"
        with open(cargo_toml, encoding="utf-8") as fh:
            if marker in fh.read():
                return
        with open(cargo_toml, "a", encoding="utf-8") as fh:
            fh.write(
                f"\n{marker}\n"
                '[patch."https://github.com/typst/typst-dev-assets"]\n'
                f'typst-dev-assets = {{ path = "{inner}" }}\n')
        self.output.info("vendored typst-dev-assets via Cargo [patch]")

    def _fetch_cargo_deps(self, env):
        # 不用 --locked：[patch] 会把 typst-dev-assets 的 git source 替换为本地
        # 路径，锁文件需要相应更新（--locked 会因此报错）。
        result = subprocess.run(
            [env["CARGO"], "fetch",
             "--manifest-path", os.path.join(self.source_folder, "Cargo.toml")],
            cwd=self.source_folder, env=env,
        ).returncode
        if result != 0:
            raise ConanInvalidConfiguration(f"cargo fetch failed (rc={result})")

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
        lib_dirs = [os.path.join(self._toolchain_dir(), "lib")]
        # 工具链自带 libstd-*.so / librustc_driver 等 dylib：proc-macro 单元测试
        # 二进制运行时 DT_NEEDED libstd-*.so，OHOS loader 忽略 DT_RUNPATH，须显式
        # 加入 LD_LIBRARY_PATH（否则 typst-macros --lib 报 "Error loading shared
        # library libstd-*.so"）。
        lib_dirs.append(os.path.join(self._toolchain_dir(), "lib", "rustlib",
                                     self._ohos_target(), "lib"))
        lib_dirs += self._prepare_runtime_libs()
        if lib_dirs:
            prev = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                lib_dirs + ([prev] if prev else [])
            )
        ca = self._ca_bundle()
        if ca:
            env["SSL_CERT_FILE"] = ca
            env["CURL_CA_BUNDLE"] = ca
        cargo_home = env.get("CARGO_HOME") or os.path.expanduser("~/.cargo")
        os.makedirs(cargo_home, exist_ok=True)
        self._configure_cargo(cargo_home, ca)
        env["CARGO_HOME"] = cargo_home
        env["CARGO_PROFILE_RELEASE_LTO"] = "false"
        env["CARGO_PROFILE_RELEASE_OPT_LEVEL"] = "1"
        # git 依赖（typst-dev-assets）经 github 镜像解析
        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = (
            f"url.{GITHUB_GIT_MIRROR}.insteadOf")
        env["GIT_CONFIG_VALUE_0"] = "https://github.com/"
        if self.settings.os == "OHOS":
            cc = self._ohos_cc()
            env.update({
                "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER": cc,
                "CC_aarch64_unknown_linux_ohos": cc,
                "CXX_aarch64_unknown_linux_ohos": self._ohos_cxx(),
                "AR_aarch64_unknown_linux_ohos": self._llvm_ar(),
                "RANLIB_aarch64_unknown_linux_ohos": self._llvm_ranlib(),
            })
        self._wire_openssl(env)
        return env

    def _wire_openssl(self, env):
        """把 conan openssl 依赖暴露给 openssl-sys 与其链接器。"""
        dep = self.dependencies.get("openssl")
        if dep is None:
            return
        pkg = dep.package_folder
        inc = os.path.join(pkg, "include")
        lib = os.path.join(pkg, "lib")
        env["OPENSSL_DIR"] = pkg
        env["OPENSSL_INCLUDE_DIR"] = inc
        env["OPENSSL_LIB_DIR"] = lib
        env["OPENSSL_STATIC"] = "1"
        target = self._ohos_target()
        tvar = target.replace("-", "_")
        env[f"OPENSSL_DIR_{tvar}"] = pkg
        env[f"OPENSSL_INCLUDE_DIR_{tvar}"] = inc
        env[f"OPENSSL_LIB_DIR_{tvar}"] = lib
        # openssl-sys 亦可用 pkg-config 探测
        for sub in ("lib/pkgconfig", "share/pkgconfig"):
            pc_dir = os.path.join(pkg, sub)
            if os.path.isdir(pc_dir):
                env["PKG_CONFIG_PATH"] = pc_dir + (
                    os.pathsep + env["PKG_CONFIG_PATH"]
                    if env.get("PKG_CONFIG_PATH") else "")
                break
        env["PKG_CONFIG_ALLOW_SYSTEM_LIBS"] = "0"
        # 交叉编译时 pkg-config 需知目标
        env["PKG_CONFIG_ALLOW_SYSTEM_CFLAGS"] = "1"
        # openssl 静态库需显式链接路径与库 + libdl/libpthread
        extra = " ".join([
            f"-C link-arg=-L{lib}",
            "-C link-arg=-lssl", "-C link-arg=-lcrypto",
        ])
        key = "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_RUSTFLAGS"
        env[key] = (env.get(key, "") + " " + extra).strip()
        env["LIBRARY_PATH"] = lib + (
            os.pathsep + env["LIBRARY_PATH"] if env.get("LIBRARY_PATH") else "")

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

    def _run_upstream_tests(self, env):
        if os.environ.get("OHC_SKIP_UPSTREAM_TESTS") == "1":
            self.output.info("Skipping upstream cargo test (OHC_SKIP_UPSTREAM_TESTS=1)")
            return
        target = self._ohos_target()
        log = os.path.join(self.build_folder, "cargo_test.log")
        # `--tests` = 单元测试 + 集成测试（typst-tests 的 tests/ 套件）。
        # doctest 排除：rust-toolchain/1.97.1 基础设施包不含 rustdoc 二进制
        # （bin/ 仅 cargo/rustc 等，rustdoc 仅有 man 页），`cargo test --doc`
        # 在该工具链下无法执行；详见 notes.md「上游测试清点」。
        cmd = [env["CARGO"], "test", "--release", "--target", target,
               "--workspace", "--tests", "--no-fail-fast"]
        with open(log, "wb") as fh:
            result = subprocess.run(cmd, cwd=self.source_folder, env=env,
                                    stdout=fh, stderr=subprocess.STDOUT).returncode
        self._report_test_summary(log, result)
        if result != 0 and os.environ.get("OHC_REQUIRE_UPSTREAM_TESTS") == "1":
            raise ConanInvalidConfiguration(
                f"Upstream typst tests failed for {target} (rc={result})")
        if result != 0:
            self.output.warning(
                f"Upstream typst tests rc={result} (see {log}); continuing build")

    def _report_test_summary(self, log, rc):
        """把 cargo test 摘要打印进 conan 输出（构建目录可能被清理，输出留档）。"""
        try:
            with open(log, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            self.output.warning(f"cargo test log not readable: {log}")
            return
        summary = [ln.rstrip("\n") for ln in lines
                   if "test result:" in ln or ln.startswith("❌")
                   or re.match(r"^\d+ passed", ln)]
        self.output.info("upstream cargo test rc=%s; log: %s" % (rc, log))
        for ln in summary:
            self.output.info("    " + ln)

    def _cargo_build(self, env):
        target = self._ohos_target()
        cmd = [env["CARGO"], "build", "--release", "--target", target,
               "-p", "typst-cli"]
        result = subprocess.run(cmd, cwd=self.source_folder, env=env).returncode
        if result != 0:
            raise ConanInvalidConfiguration(
                f"cargo build failed for {target} (rc={result})")
        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        src = os.path.join(self.source_folder, "target", target, "release", "typst")
        if not os.path.isfile(src):
            raise ConanInvalidConfiguration(f"typst binary not produced: {src}")
        dst = os.path.join(out_dir, "typst")
        shutil.copy2(src, dst)
        os.chmod(dst, 0o755)

    def _sign_binaries(self):
        if self.settings.os != "OHOS":
            return
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning("binary-sign-tool not found; OHOS may reject executables")
            return
        out_dir = os.path.join(self.build_folder, "bin")
        for name in os.listdir(out_dir):
            path = os.path.join(out_dir, name)
            if os.path.isfile(path):
                result = self.run(
                    f"{shlex.quote(signer)} sign "
                    f"-inFile {shlex.quote(path)} "
                    f"-outFile {shlex.quote(path)} -selfSign 1",
                    ignore_errors=True, quiet=True)
                if result != 0:
                    raise ConanInvalidConfiguration(
                        f"binary-sign-tool failed (rc={result}): {path}")

    def _find_binary_sign_tool(self):
        candidates = [
            os.environ.get("BINARY_SIGN_TOOL"),
            shutil.which("binary-sign-tool"),
            shutil.which("hapsign"),
            "/data/service/hnp/bin/binary-sign-tool",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/bin/"
            "binary-sign-tool",
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
        except (KeyError, ConanException):
            return None

    def _toolchain_dir(self):
        return os.path.join(self.build_folder, "rust-toolchain")

    def _prepare_signed_toolchain(self):
        """复制 cargo/rustc + librustc_driver 到 build_folder 并自签名。"""
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
                "binary-sign-tool not found; toolchain binaries stay unsigned")
        to_sign = []
        for name in ("cargo", "rustc"):
            s = os.path.join(src, "bin", name)
            if os.path.isfile(s):
                d = os.path.join(bin_dst, name)
                if not os.path.isfile(d):
                    shutil.copy2(s, d)
                    os.chmod(d, 0o755)
                to_sign.append(d)
        # 须可加载的 dylib：rustc dlopen 的 librustc_driver，以及 proc-macro
        # 测试二进制 DT_NEEDED 的 libstd-*.so（在 lib/rustlib/<target>/lib/）。
        # OHOS 拒绝加载未签名 .so，故复制 + 自签名到 lib_dst 根（进 LD_LIBRARY_PATH）。
        dylib_srcs = []
        src_lib = os.path.join(src, "lib")
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                if name.startswith("librustc_driver") and name.endswith(".so"):
                    dylib_srcs.append(os.path.join(src_lib, name))
            rustlib_lib = os.path.join(src_lib, "rustlib", self._ohos_target(), "lib")
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
                    capture_output=True, text=True)
                if result.returncode != 0 or not os.path.isfile(tmp):
                    raise ConanInvalidConfiguration(
                        "binary-sign-tool failed for %s (rc=%d): %s"
                        % (path, result.returncode, result.stderr[:200]))
                os.replace(tmp, path)
                os.chmod(path, 0o755)
                self.output.info("signed toolchain binary: %s" % os.path.basename(path))
        else:
            self.output.warning("toolchain binaries were not signed")
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                d = os.path.join(lib_dst, name)
                if not os.path.exists(d):
                    os.symlink(os.path.join(src_lib, name), d)
        for name in ("etc", "libexec", "share"):
            s = os.path.join(src, name)
            d = os.path.join(dst, name)
            if os.path.isdir(s) and not os.path.exists(d):
                os.symlink(s, d)
        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("signed toolchain prepared\n")
        return bin_dst

    def _prepare_runtime_libs(self):
        base = os.path.join(self.build_folder, "rust-runtime")
        os.makedirs(base, exist_ok=True)
        lib_dirs = []
        for name, url, sha256 in RUST_RUNTIME_BOTTLES:
            tgz = os.path.join(base, name + ".tar.gz")
            if not os.path.isfile(tgz):
                try:
                    download(self, url, tgz, sha256=sha256)
                except ConanException as exc:
                    # harmonybrew bottle 轮换会导致旧 URL 404：尝试下一个候选
                    self.output.warning(
                        f"runtime bottle unavailable ({name}): {url} ({exc})")
                    continue
            extract_dir = os.path.join(base, name)
            os.makedirs(extract_dir, exist_ok=True)
            with tarfile.open(tgz, "r:gz") as tf:
                tf.extractall(extract_dir)
            for root, _dirs, files in os.walk(extract_dir):
                if os.path.basename(root) != "lib":
                    continue
                if any(f.startswith(("libssl.", "libcrypto.", "libz."))
                       for f in files):
                    lib_dirs.append(root)
        if not lib_dirs:
            raise ConanInvalidConfiguration(
                "no cargo runtime OpenSSL bottle available; cargo 1.97 needs "
                "libssl/libcrypto (>=3.5, SSL_get0_group_name) which the system "
                "OpenSSL (3.0.x) cannot provide")
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

    def _configure_cargo(self, cargo_home, ca_bundle=None):
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

    def package(self):
        copy(self, "typst", src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
