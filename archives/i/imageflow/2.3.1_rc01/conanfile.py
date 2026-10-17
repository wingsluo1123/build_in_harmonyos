#!/usr/bin/env python3
"""Conan recipe for imageflow 2.3.1_rc01 (Rust workspace + C components).

imageflow is a fast, secure image processing library and CLI:
  * libimageflow.so - stable C ABI (crate imageflow_abi, cdylib)
  * imageflow_tool  - command-line tool (crate imageflow_tool)

This recipe cross-builds the Rust 2024 workspace for HarmonyOS PC
(aarch64-unknown-linux-ohos) with the Rust toolchain from the artifact
repository (rust-toolchain/1.97.1, tool_requires; host == target). Standard
rustup cannot bootstrap on HarmonyOS (E105/E154) and CI has no system cargo.

Platform notes (full log in notes.md):
  * rust-toolchain dist binaries ship unsigned; HarmonyOS refuses execve of
    unsigned ELF (EACCES), so cargo/rustc/librustc_driver are copied into the
    build folder and signed with binary-sign-tool -selfSign 1 (below/0.11.0
    precedent).
  * cargo 1.97 dynamically requires OpenSSL 3.5+ (SSL_get0_group_name); the
    artifact repository ships openssl as a static package (R26), so its static
    PIC archives are relinked into private shared objects under
    build_folder/cargo-runtime (cbindgen/0.28.0 precedent). libz.so is
    relinked from zlib-ng-compat/2.3.3 (system zlib as fallback).
  * The source tarball has no .git; imageflow_types/build.rs embeds git
    metadata, so the pinned tag values are passed via environment variables
    exactly as upstream Cross.toml does for container builds.
  * Cargo git dependencies (imazen libpng-sys / lcms2-sys forks and
    rust-custom-derive) carry `vendor` submodules. If GitHub is unreachable
    the fetch is retried with git's url.insteadOf -> ghfast.top (E017), which
    proxies both clone and submodule traffic.
  * imageflow_tool and libimageflow.so are signed after the build so the
    conan cache copy stays executable under HarmonyOS code-signing.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

RUST_TARGET = "aarch64-unknown-linux-ohos"
GITHUB_MIRROR = "https://ghfast.top/https://github.com/"

# v2.3.1-rc01 tag object (source tarballs carry no .git; upstream Cross.toml
# passes the equivalent metadata via env vars for cross containers).
GIT_METADATA = {
    "GIT_COMMIT": "0635e3863f950fa58c227eaec1d4b957e0f42fdc",
    "GIT_COMMIT_SHORT": "0635e3863",
    "GIT_DESCRIBE_ALWAYS": "v2.3.1-rc01",
    "GIT_DESCRIBE_ALWAYS_LONG": "v2.3.1-rc01-0-g0635e3863f",
    "GIT_OPTIONAL_TAG": "v2.3.1-rc01",
}


class ImageflowConan(ConanFile):
    name = "imageflow"
    version = "2.3.1_rc01"
    description = ("imageflow: fast, secure image processing library and "
                   "command-line tool (libimageflow C ABI + imageflow_tool)")
    license = "AGPL-3.0-or-later"
    homepage = "https://github.com/imazen/imageflow"
    url = "https://github.com/imazen/imageflow"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # Rust 工具链由制品仓基础设施包提供（R36）：rust-lang 官方 dist
        # 预编译，宿主与目标均为 aarch64-unknown-linux-ohos。
        self.tool_requires("rust-toolchain/1.97.1")
        # cargo 1.97 运行期需要 OpenSSL 3.5+（SSL_get0_group_name）；制品仓
        # openssl 为静态包（R26），构建期重链为私有 .so（cbindgen 先例）。
        self.tool_requires("openssl/3.5.6.1.1")
        # cargo 运行期 NEEDED libz.so；zlib-ng-compat 静态包（R26）重链复用。
        self.tool_requires("zlib-ng-compat/2.3.3")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")
        if str(self.settings.arch) not in ("armv8", "arm64", "aarch64"):
            raise ConanInvalidConfiguration(
                f"Unsupported arch: {self.settings.arch} "
                "(the Rust OHOS target is aarch64)")
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "imageflow builds the libimageflow cdylib only; "
                "set -o imageflow/*:shared=True")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self._prepare_signed_toolchain()
        self._prepare_cargo_runtime()
        env = self._rust_environment()
        self._fetch_cargo_deps(env)
        self._cargo_build(env)
        self._sign_artifacts(env)

    # ---------------------------------------------------------------- helpers

    def _dep_folder(self, name):
        try:
            return self.dependencies.build[name].package_folder
        except (KeyError, ConanException):
            return None

    def _find_binary_sign_tool(self):
        candidates = [
            os.environ.get("BINARY_SIGN_TOOL"),
            shutil.which("binary-sign-tool"),
            "/data/service/hnp/bin/binary-sign-tool",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
            "ohos/native/bin/binary-sign-tool",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _ohos_cc(self):
        candidates = [
            "/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/"
            "llvm/bin/aarch64-unknown-linux-ohos-clang",
            shutil.which("aarch64-unknown-linux-ohos-clang"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "aarch64-unknown-linux-ohos-clang not found")

    def _ohos_cxx(self):
        cc = self._ohos_cc()
        return cc + "++" if not cc.endswith("++") else cc

    def _llvm_tool(self, name):
        directory = os.path.dirname(self._ohos_cc())
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate):
            return candidate
        found = shutil.which(name)
        if found:
            return found
        raise ConanInvalidConfiguration(f"{name} not found")

    def _toolchain_dir(self):
        return os.path.join(self.build_folder, "rust-toolchain")

    def _prepare_signed_toolchain(self):
        """Copy + sign cargo/rustc/librustc_driver; symlink the read-only rest.

        rust-toolchain/1.97.1 carries unsigned rust-lang dist binaries;
        HarmonyOS refuses execve of unsigned ELF (EACCES errno 13). Signing
        happens into the build folder, the conan cache stays untouched.
        """
        dst = self._toolchain_dir()
        bin_dst = os.path.join(dst, "bin")
        lib_dst = os.path.join(dst, "lib")
        if os.path.isfile(os.path.join(dst, ".prepared")):
            return
        src = self._dep_folder("rust-toolchain")
        if not src:
            raise ConanInvalidConfiguration(
                "rust-toolchain/1.97.1 tool_requires package not available")
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)
        signer = self._find_binary_sign_tool()
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool not found; OHOS rejects unsigned rust "
                "toolchain binaries (EACCES)")

        to_sign = []
        for name in ("cargo", "rustc"):
            source = os.path.join(src, "bin", name)
            if os.path.isfile(source):
                target = os.path.join(bin_dst, name)
                if not os.path.isfile(target):
                    shutil.copy2(source, target)
                    os.chmod(target, 0o755)
                to_sign.append(target)
        src_lib = os.path.join(src, "lib")
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                if name.startswith("librustc_driver") and name.endswith(".so"):
                    target = os.path.join(lib_dst, name)
                    if not os.path.isfile(target):
                        shutil.copy2(os.path.join(src_lib, name), target)
                        os.chmod(target, 0o755)
                    to_sign.append(target)

        for path in to_sign:
            tmp = path + ".signed"
            result = subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", tmp,
                 "-selfSign", "1"],
                capture_output=True, text=True)
            if result.returncode != 0 or not os.path.isfile(tmp):
                raise ConanInvalidConfiguration(
                    "binary-sign-tool failed for %s (rc=%d): %s"
                    % (path, result.returncode, result.stderr[:300]))
            os.replace(tmp, path)
            os.chmod(path, 0o755)
            self.output.info("signed toolchain binary: %s"
                             % os.path.basename(path))

        # Remaining read-only payload (rustlib/, proc-macro dylibs, ...) is
        # symlinked so rustc finds its sysroot without copying ~500 MB.
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                target = os.path.join(lib_dst, name)
                if not os.path.exists(target):
                    os.symlink(os.path.join(src_lib, name), target)
        for name in ("etc", "libexec", "share"):
            source = os.path.join(src, name)
            target = os.path.join(dst, name)
            if os.path.isdir(source) and not os.path.exists(target):
                os.symlink(source, target)
        with open(os.path.join(dst, ".prepared"), "w", encoding="utf-8") as fh:
            fh.write("signed toolchain prepared\n")

    def _prepare_cargo_runtime(self):
        """Relink static OpenSSL/zlib archives into private shared objects.

        cargo is dynamically linked against libssl.so/libcrypto.so/libz.so and
        OHOS ignores DT_RUNPATH, so the private runtime dir is prepended to
        LD_LIBRARY_PATH for every cargo subprocess. Keep everything under
        build_folder (R49): no shared prefix is touched.
        """
        runtime = os.path.join(self.build_folder, "cargo-runtime")
        os.makedirs(runtime, exist_ok=True)
        cc = self._ohos_cc()

        def find_archive(base, filename):
            for root, _dirs, files in os.walk(base):
                if filename in files:
                    return os.path.join(root, filename)
            return None

        openssl = self._dep_folder("openssl")
        if not openssl:
            raise ConanInvalidConfiguration(
                "openssl/3.5.6.1.1 tool_requires package not available")
        crypto_out = os.path.join(runtime, "libcrypto.so")
        ssl_out = os.path.join(runtime, "libssl.so")
        if not os.path.isfile(crypto_out):
            archive = find_archive(openssl, "libcrypto.a")
            if not archive:
                raise ConanInvalidConfiguration("libcrypto.a not found in openssl package")
            self._relink(cc, [archive], crypto_out, "libcrypto.so",
                         ["-ldl", "-pthread"])
        if not os.path.isfile(ssl_out):
            archive = find_archive(openssl, "libssl.a")
            if not archive:
                raise ConanInvalidConfiguration("libssl.a not found in openssl package")
            self._relink(cc, [archive], ssl_out, "libssl.so",
                         ["-L" + runtime, "-lcrypto", "-ldl", "-pthread"])

        zlib_out = os.path.join(runtime, "libz.so")
        if not os.path.exists(zlib_out):
            zlib_pkg = self._dep_folder("zlib-ng-compat")
            archive = find_archive(zlib_pkg, "libz.a") if zlib_pkg else None
            if archive:
                self._relink(cc, [archive], zlib_out, "libz.so", [])
            else:
                system_zlib = None
                for candidate in ("/usr/lib/libz.so.1", "/lib/libz.so.1",
                                  "/usr/lib64/libz.so.1",
                                  os.path.expanduser("~/usr/local/lib/libz.so"),
                                  os.path.expanduser("~/.harmonybrew/lib/libz.so")):
                    if os.path.exists(candidate):
                        system_zlib = candidate
                        break
                if not system_zlib:
                    raise ConanInvalidConfiguration(
                        "libz.so not available for the cargo runtime")
                os.symlink(system_zlib, zlib_out)
                self.output.warning(
                    "zlib-ng-compat archive not found; using system zlib %s"
                    % system_zlib)

    def _relink(self, cc, archives, output, soname, extra):
        command = [cc, "-shared", "-Wl,-z,relro,-z,now",
                   "-Wl,-soname," + soname]
        for archive in archives:
            command += ["-Wl,--whole-archive", archive, "-Wl,--no-whole-archive"]
        command += list(extra) + ["-o", output]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                "failed to relink %s (rc=%d): %s"
                % (soname, result.returncode, result.stderr[:300]))

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

    def _configure_cargo(self, cargo_home, ca_bundle):
        os.makedirs(cargo_home, exist_ok=True)
        config_path = os.path.join(cargo_home, "config.toml")
        content = (
            "[source.crates-io]\n"
            "replace-with = \"rsproxy-sparse\"\n\n"
            "[source.rsproxy-sparse]\n"
            "registry = \"sparse+https://rsproxy.cn/index/\"\n\n"
            "[net]\n"
            "git-fetch-with-cli = true\n"
            "retry = 5\n"
        )
        if ca_bundle:
            content += ("\n[http]\n"
                        "cainfo = \"%s\"\n" % ca_bundle)
        with open(config_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)

    def _rust_environment(self):
        env = os.environ.copy()
        toolchain = self._toolchain_dir()
        runtime = os.path.join(self.build_folder, "cargo-runtime")
        env["CARGO"] = os.path.join(toolchain, "bin", "cargo")

        path_parts = [os.path.join(toolchain, "bin"), runtime]
        for directory in ("/data/service/hnp/bin", "/system/bin",
                          "/system/sbin", "/vendor/bin"):
            if os.path.isdir(directory):
                path_parts.append(directory)
        env["PATH"] = os.pathsep.join(path_parts) + os.pathsep + env.get("PATH", "")

        lib_parts = [runtime, os.path.join(toolchain, "lib")]
        if env.get("LD_LIBRARY_PATH"):
            lib_parts.append(env["LD_LIBRARY_PATH"])
        env["LD_LIBRARY_PATH"] = os.pathsep.join(lib_parts)

        ca_bundle = self._ca_bundle()
        if ca_bundle:
            env["SSL_CERT_FILE"] = ca_bundle
            env["CURL_CA_BUNDLE"] = ca_bundle
            env["CARGO_HTTP_CAINFO"] = ca_bundle
            env["GIT_SSL_CAINFO"] = ca_bundle

        cargo_home = env.get("CARGO_HOME") or os.path.expanduser("~/.cargo")
        self._configure_cargo(cargo_home, ca_bundle)
        env["CARGO_HOME"] = cargo_home

        tmpdir = env.get("TMPDIR") or os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env["TMPDIR"] = tmpdir

        env["CC_" + RUST_TARGET.replace("-", "_")] = self._ohos_cc()
        env["CXX_" + RUST_TARGET.replace("-", "_")] = self._ohos_cxx()
        env["AR_" + RUST_TARGET.replace("-", "_")] = self._llvm_tool("llvm-ar")
        env["RANLIB_" + RUST_TARGET.replace("-", "_")] = self._llvm_tool("llvm-ranlib")
        env["CARGO_TARGET_" + RUST_TARGET.upper().replace("-", "_")
            + "_LINKER"] = self._ohos_cc()
        # L5a 质量门禁：cdylib 需要 DT_SONAME（下游链接器按 SONAME 寻址）。
        # 该 RUSTFLAGS 对所有 target 链接步骤生效；可执行文件上记录 SONAME
        # 对 OHOS loader 无害（实测 imageflow_tool --version 正常）。
        env["CARGO_TARGET_" + RUST_TARGET.upper().replace("-", "_")
            + "_RUSTFLAGS"] = "-C link-arg=-Wl,-soname,libimageflow.so"
        env["CARGO_TARGET_DIR"] = os.path.join(self.build_folder, "target")
        env["CARGO_NET_RETRY"] = "5"
        env.update(GIT_METADATA)
        return env

    def _github_reachable(self, env):
        if os.environ.get("OHC_CARGO_GIT_MIRROR") == "1":
            return False
        try:
            result = subprocess.run(
                ["git", "ls-remote",
                 "https://github.com/imazen/imageflow.git", "HEAD"],
                env=env, capture_output=True, text=True, timeout=25)
            return result.returncode == 0
        except Exception:
            return False

    def _git_mirror_env(self, env):
        mirrored = dict(env)
        mirrored["GIT_CONFIG_COUNT"] = "1"
        mirrored["GIT_CONFIG_KEY_0"] = "url." + GITHUB_MIRROR + ".insteadOf"
        mirrored["GIT_CONFIG_VALUE_0"] = "https://github.com/"
        return mirrored

    def _fetch_cargo_deps(self, env):
        fetch_env = env
        if not self._github_reachable(env):
            self.output.info("GitHub unreachable from build host; routing cargo "
                            "git dependencies through ghfast.top (E017)")
            fetch_env = self._git_mirror_env(env)
        result = subprocess.run([env["CARGO"], "fetch", "--locked"],
                                cwd=self.source_folder, env=fetch_env)
        if result.returncode != 0 and fetch_env is env:
            self.output.warning("cargo fetch failed; retrying via ghfast.top mirror")
            fetch_env = self._git_mirror_env(env)
            result = subprocess.run([env["CARGO"], "fetch", "--locked"],
                                    cwd=self.source_folder, env=fetch_env)
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                "cargo fetch failed (rc=%d)" % result.returncode)

    def _cargo_build(self, env):
        command = [env["CARGO"], "build", "--locked", "--release",
                   "--workspace", "--target", RUST_TARGET]
        result = subprocess.run(command, cwd=self.source_folder, env=env)
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                "cargo build failed for %s (rc=%d)"
                % (RUST_TARGET, result.returncode))

    def _release_dir(self, env):
        return os.path.join(env["CARGO_TARGET_DIR"], RUST_TARGET, "release")

    def _sign_artifacts(self, env):
        signer = self._find_binary_sign_tool()
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool not found; cannot sign packaged artifacts")
        release_dir = self._release_dir(env)
        for name in ("imageflow_tool", "libimageflow.so"):
            path = os.path.join(release_dir, name)
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(
                    "expected build artifact missing: %s" % path)
            tmp = path + ".signed"
            result = subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", tmp,
                 "-selfSign", "1"],
                capture_output=True, text=True)
            if result.returncode != 0 or not os.path.isfile(tmp):
                raise ConanInvalidConfiguration(
                    "binary-sign-tool failed for %s (rc=%d): %s"
                    % (name, result.returncode, result.stderr[:300]))
            os.replace(tmp, path)
            os.chmod(path, 0o755)
            self.output.info("signed artifact: %s" % name)

    # --------------------------------------------------------------- packages

    def package(self):
        release_dir = os.path.join(self.build_folder, "target",
                                   RUST_TARGET, "release")
        copy(self, "imageflow_tool", release_dir,
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "libimageflow.so", release_dir,
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.h",
             os.path.join(self.source_folder, "bindings", "headers"),
             os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "LICENSE*", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["imageflow"]
        self.cpp_info.bindirs = ["bin"]
