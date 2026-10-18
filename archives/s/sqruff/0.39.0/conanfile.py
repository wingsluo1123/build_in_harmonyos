#!/usr/bin/env python3
"""Conan recipe — sqruff 0.39.0 (Cargo / Rust, HarmonyOS PC aarch64).

sqruff is a high-speed SQL linter and formatter written in Rust
(quarylabs/sqruff, Apache-2.0). The cargo workspace builds a single CLI
binary ``sqruff`` (default member ``crates/cli``; ``[[bin]] name =
"sqruff"``) exposing the ``lint`` / ``fix`` / ``parse`` / ``rules`` /
``templaters`` / ``lsp`` subcommands — the LSP server is embedded in the
same binary (``sqruff lsp`` → sqruff_lsp::run()).

OHOS 适配要点（全部依赖来自 ohpcd 制品仓，无任何外部 URL 依赖）：
1. 工具链（R36）：``rust-toolchain/1.97.1``（ohpcd 制品仓基础设施包，
   ``tool_requires``）提供 cargo/rustc 与 aarch64-unknown-linux-ohos 标准库，
   宿主与目标一致、原生可执行。Conan 解包不带可执行位、且 OHOS 拒绝执行
   未签名 ELF，故 cargo/rustc/librustc_driver 复制到构建目录私有副本，先探测
   可执行性、失败才用 binary-sign-tool 自签名，其余只读负载软链接（保持
   rustc sysroot 推断；tracexec/0.17.0、below/0.11.0、comet/0.3.2 先例）。
   不使用 rustup 引导（标准 rustup 无法识别 HarmonyOS 宿主，E105/E154）。
2. cargo 运行期共享库：cargo 1.97 动态链接 libssl.so/libcrypto.so。用制品仓
   ``openssl/3.5.6.1.1``（``tool_requires``）的 PIC 静态库重链为私有 DSO，
   仅本包构建环境 LD_LIBRARY_PATH 可见，不写任何公共前缀（comet/0.3.2 先例；
   R49）。历史教训：harmonybrew bottle URL 仅保留每公式最新版，固定版本 URL
   会 404（2026-10-15 CI #93066 实测），故不采用 bottle 下载。
3. crates.io 走 rsproxy.cn 稀疏镜像（写入构建目录私有的 CARGO_HOME/config.toml，
   不落源码树、不落共享前缀），并显式指定 CA（系统证书或 conan 自带 certifi）。
4. 上游测试（R51）：完整上游 cargo 套件在 build() 内真实执行（workspace 除
   pyo3/wasm 平台绑定 crate 外全量；rules/templaters 中依赖 pyo3/Python 绑定的
   用例按上游官方开关 SQRUFF_SKIP_UNSUPPORTED_TEMPLATERS=1 跳过并如实申报）。
   计数从真实 "test result:" 行解析、写入 res/upstream_test_result.json 随包
   携带；test_package 重发 HMBS_UPSTREAM_TEST_RESULT 并对计数硬校验
   （tlsx/1.2.2 约定：hmbs 只从 test_package 阶段 stdout 采集该标记）。
"""
import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

OHOS_TARGET = "aarch64-unknown-linux-ohos"
_OHOS_TARGET_ENV = OHOS_TARGET.upper().replace("-", "_")

BINARY_NAME = "sqruff"

# 硬门禁：上游套件在 OHOS 上应通过的全部 libtest 用例数（159 passed：
# sqruff-lib 77 + lib-core 30 + sqlinference 13 + lineage 16 + lsp 5 +
# cli-lib 8 + cli 8 + dialects 2；另有 4 例上游自带 ignore、0 filtered）。
UPSTREAM_EXPECTED_PASSED = 159

# harness=false 集成测试二进制必须在日志中出现（其无 "test result:" 行，
# 按退出码判定；cargo 命令整体 rc!=0 即失败）。
_HARNESS_FALSE_TARGETS = (
    "ui.rs", "ui_github.rs", "ui_json.rs", "fix_return_code.rs",
    "fix_parse_errors.rs", "config_not_found.rs", "configure_rule.rs",
    "dialect_override.rs", "none_format.rs",
)

# OHOS 拒绝执行无执行位/未签名的 ELF（Conan 包内文件权限固定）
_SIGN_TOOL_CANDIDATES = (
    "/data/service/hnp/bin/binary-sign-tool",
    "binary-sign-tool",
)

# 共享 worker 资源耗尽（posix_spawn "Resource temporarily unavailable" 等）
# 时以 CARGO_BUILD_JOBS=1 重试一次（cargo 增量续跑，成本低）。
_RESOURCE_EXHAUSTION_MARKERS = (
    "Resource temporarily unavailable",
    "posix_spawn failed",
    "Cannot allocate memory",
    "error: could not spawn",
)


class SqruffConan(ConanFile):
    name = "sqruff"
    version = "0.39.0"
    description = "A high-speed SQL linter and formatter written in Rust"
    license = "Apache-2.0"
    homepage = "https://github.com/quarylabs/sqruff"
    url = "https://github.com/quarylabs/sqruff"
    topics = ("sql", "linter", "formatter", "rust")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # 导出 conandata.yml 声明的补丁（当前 patches: {}，为 0 补丁；
        # 保留标准管线，后续适配修复可直接加补丁而不改配方结构）
        export_conandata_patches(self)

    def build_requirements(self):
        # R36：Rust 工具链与 cargo 运行期 OpenSSL 均来自制品仓已发布包。
        self.tool_requires("rust-toolchain/1.97.1")
        self.tool_requires("openssl/3.5.6.1.1")

    def validate(self):
        # R32: settings.os check must use in (Linux, OHOS)
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sqruff supports Linux and OHOS only, got {self.settings.os}"
            )
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration(
                f"Unsupported arch: {self.settings.arch}")
        if str(self.settings.build_type) != "Release":
            raise ConanInvalidConfiguration("Release build_type is required")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # ── toolchain（tracexec/0.17.0 范式） ───────────────────────────────

    def _toolchain_root(self):
        return os.path.join(self.build_folder, "rust-toolchain")

    def _prepare_toolchain(self, runtime_dirs):
        """Copy cargo/rustc into a private, executable toolchain root.

        Conan's payload has no executable bit and OHOS refuses unsigned ELF,
        so cargo/rustc (and the librustc_driver that rustc dlopens) are copied
        and self-signed with the OHOS binary-sign-tool whenever the probe
        cannot start them; the remaining read-only payload is symlinked,
        which keeps rustc's sysroot inference intact.
        """
        dep = self.dependencies.build.get("rust-toolchain")
        if not dep:
            raise ConanInvalidConfiguration(
                "rust-toolchain/1.97.1 tool_requires is required")
        src = dep.package_folder
        root = self._toolchain_root()
        bin_dst = os.path.join(root, "bin")
        lib_dst = os.path.join(root, "lib")
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)

        executables = []
        for name in ("cargo", "rustc"):
            source = os.path.join(src, "bin", name)
            if not os.path.isfile(source):
                raise ConanInvalidConfiguration(
                    f"rust-toolchain payload is missing bin/{name}")
            target = os.path.join(bin_dst, name)
            shutil.copy2(source, target)
            os.chmod(target, 0o755)
            executables.append(target)

        src_lib = os.path.join(src, "lib")
        symlink_later = []
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                source = os.path.join(src_lib, name)
                if name.startswith("librustc_driver") and name.endswith(".so"):
                    target = os.path.join(lib_dst, name)
                    shutil.copy2(source, target)
                    os.chmod(target, 0o755)
                    executables.append(target)
                    continue
                symlink_later.append(name)
        for name in symlink_later:
            self._link(os.path.join(src_lib, name),
                       os.path.join(lib_dst, name))
        for name in ("etc", "libexec", "share"):
            source = os.path.join(src, name)
            if os.path.isdir(source):
                self._link(source, os.path.join(root, name))

        if not self._toolchain_runs(bin_dst, lib_dst, runtime_dirs):
            self._sign(executables)
            if not self._toolchain_runs(bin_dst, lib_dst, runtime_dirs):
                raise ConanInvalidConfiguration(
                    "rust-toolchain cargo/rustc cannot be executed on OHOS")
        return bin_dst, lib_dst

    @staticmethod
    def _link(source, target):
        if not os.path.exists(target) and not os.path.islink(target):
            os.symlink(source, target)

    def _toolchain_runs(self, bin_dst, lib_dst, runtime_dirs):
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [lib_dst, *runtime_dirs, env.get("LD_LIBRARY_PATH", "")])
        try:
            proc = subprocess.run([os.path.join(bin_dst, "cargo"), "--version"],
                                  capture_output=True, text=True,
                                  env=env, timeout=120)
        except (OSError, subprocess.SubprocessError) as exc:
            self.output.warning(f"cargo probe failed: {exc}")
            return False
        if proc.returncode == 0:
            self.output.info(f"toolchain: {proc.stdout.strip()}")
        else:
            self.output.warning(
                f"cargo probe rc={proc.returncode}: {proc.stderr.strip()[:200]}")
        return proc.returncode == 0

    def _find_binary_sign_tool(self):
        candidates = list(_SIGN_TOOL_CANDIDATES)
        home = os.path.expanduser("~")
        candidates += [
            os.environ.get("BINARY_SIGN_TOOL"),
            shutil.which("binary-sign-tool"),
            shutil.which("hapsign"),
            "/data/service/hnp/ohos-sdk.org/"
            "ohos-sdk_26.0.0.18/ohos/native/bin/binary-sign-tool",
            os.path.join(home, ".harmonybrew", "opt", "ohos-sdk@26.0.0.18",
                         "bin", "binary-sign-tool"),
            os.path.join(home, ".harmonybrew", "Cellar", "ohos-sdk@26.0.0.18",
                         "26.0.0.18", "bin", "binary-sign-tool"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _sign(self, paths):
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; the OHOS loader may reject the "
                "binaries")
            return
        for path in paths:
            signed = path + ".signed"
            proc = subprocess.run(
                [signer, "sign", "-inFile", path, "-outFile", signed,
                 "-selfSign", "1"], capture_output=True, text=True)
            if proc.returncode != 0 or not os.path.isfile(signed):
                self.output.warning(f"binary-sign-tool failed for {path}")
                continue
            os.replace(signed, path)
            os.chmod(path, 0o755)

    # ── cargo runtime（openssl 私有 DSO；comet/0.3.2 范式） ─────────────

    def _sdk_lib_dir(self, cc):
        """OHOS SDK llvm/lib: the bundled lld needs its libxml2.so.16."""
        binary_dir = os.path.dirname(os.path.realpath(cc))
        candidate = os.path.join(os.path.dirname(binary_dir), "lib")
        return candidate if os.path.isdir(candidate) else ""

    def _compilers(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c") or shutil.which("clang") \
            or "/data/service/hnp/bin/clang"
        cxx = compilers.get("cpp") or shutil.which("clang++") \
            or "/data/service/hnp/bin/clang++"
        return cc, cxx

    def _prepare_cargo_runtime(self, cc):
        """Relink the published PIC OpenSSL archives into private DSOs.

        cargo 1.97 dynamically links libssl.so/libcrypto.so. The published
        openssl/3.5.6.1.1 package ships PIC static archives; relink them into
        a private directory consumed only by this recipe's LD_LIBRARY_PATH —
        no system prefix or public Conan lib directory receives a shared
        object (comet/0.3.2 先例；R49).
        """
        openssl = Path(self.dependencies.build["openssl"].package_folder)
        runtime = Path(self.build_folder) / "cargo-runtime"
        runtime.mkdir(exist_ok=True)
        for name in ("crypto", "ssl"):
            archive = next(openssl.rglob("lib" + name + ".a"), None)
            if archive is None:
                raise ConanInvalidConfiguration(
                    f"openssl static archive lib{name}.a not found in the "
                    "openssl/3.5.6.1.1 package")
            command = [cc, "-shared", "-Wl,-z,relro,-z,now",
                       "-Wl,-soname,lib" + name + ".so",
                       "-Wl,--whole-archive", str(archive),
                       "-Wl,--no-whole-archive", "-ldl", "-pthread"]
            if name == "ssl":
                command += ["-L" + str(runtime), "-lcrypto"]
            command += ["-o", str(runtime / ("lib" + name + ".so"))]
            proc = subprocess.run(command, capture_output=True, text=True)
            if proc.returncode != 0 or not (runtime / ("lib" + name + ".so")).is_file():
                raise ConanException(
                    "relinking OpenSSL shared library failed: "
                    + (proc.stderr or "")[-2000:])
        return [str(runtime)]

    # ── build environment（R33: every variable defined here） ─────────

    def _ca_bundle(self):
        candidates = [
            os.environ.get("SSL_CERT_FILE"),
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
            os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        try:
            import certifi
            candidate = certifi.where()
            if candidate and os.path.isfile(candidate):
                return candidate
        except ImportError:
            pass
        return None

    def _build_env(self, bin_dst, lib_dst, runtime_dirs):
        cc, cxx = self._compilers()
        cargo_home = os.path.join(self.build_folder, "cargo-home")
        tmpdir = os.environ.get("HMBS_TMPDIR") \
            or os.path.join(self.build_folder, "tmp")
        for directory in (cargo_home, tmpdir):
            os.makedirs(directory, exist_ok=True)

        ca_bundle = self._ca_bundle()
        # crates.io 走 rsproxy.cn 稀疏镜像 + 网络容错 + CA（构建目录私有
        # CARGO_HOME，不落源码树、不落共享前缀）。
        with open(os.path.join(cargo_home, "config.toml"), "w",
                  encoding="utf-8", newline="\n") as handle:
            handle.write(
                '[source.crates-io]\nreplace-with = "rsproxy-sparse"\n'
                '[source.rsproxy-sparse]\n'
                'registry = "sparse+https://rsproxy.cn/index/"\n'
                "[net]\nretry = 10\ngit-fetch-with-cli = true\n"
                "[http]\ntimeout = 600\nlow-speed-limit = 1\n"
                "multiplexing = false\n"
            )
            if ca_bundle:
                handle.write(f'cainfo = "{ca_bundle}"\n')

        env = dict(os.environ)
        for name in ("RUSTFLAGS", "RUSTC", "CARGO", "CARGO_BUILD_TARGET"):
            env.pop(name, None)
        path_parts = [bin_dst]
        hnp_bin = "/data/service/hnp/bin"
        if os.path.isdir(hnp_bin):
            path_parts.append(hnp_bin)
        lib_parts = [lib_dst, *runtime_dirs]
        sdk_lib = self._sdk_lib_dir(cc)
        if sdk_lib:
            lib_parts.append(sdk_lib)
        env.update({
            "CARGO": os.path.join(bin_dst, "cargo"),
            "PATH": os.pathsep.join(path_parts + [env.get("PATH", "")]),
            "LD_LIBRARY_PATH": os.pathsep.join(
                lib_parts + [env.get("LD_LIBRARY_PATH", "")]),
            "CARGO_HOME": cargo_home,
            "CARGO_BUILD_JOBS": "4",
            "CARGO_NET_RETRY": "10",
            "CARGO_HTTP_TIMEOUT": "600",
            "TMPDIR": tmpdir,
            "TMP": tmpdir,
            "TEMP": tmpdir,
            "CC": cc,
            "CXX": cxx,
            # 任何经 cc 编译 C++ 的 crate（build.rs）默认发 -lstdc++，
            # OHOS SDK 只提供 libc++。
            "CXXSTDLIB": "c++",
            "RUSTFLAGS": "-C linker=" + cc,
            f"CARGO_TARGET_{_OHOS_TARGET_ENV}_LINKER": cc,
        })
        if ca_bundle:
            env["SSL_CERT_FILE"] = ca_bundle
            env["CURL_CA_BUNDLE"] = ca_bundle
            env["CARGO_HTTP_CAINFO"] = ca_bundle
        return env

    def _cargo(self, env, subcommand, extra):
        """cargo 命令行（--config 为最高优先级配置来源）。"""
        linker = self._compilers()[0]
        return ([env["CARGO"], "--config",
                 'target.%s.linker="%s"' % (OHOS_TARGET, linker),
                 subcommand] + list(extra))

    def _run(self, command, env, timeout, check=True, log_path=None):
        self.output.info(f"$ {shlex.join(command)}")
        proc = subprocess.run(command, cwd=self.source_folder, env=env,
                              capture_output=True, text=True, timeout=timeout)
        output = (proc.stdout or "") + (proc.stderr or "")
        print(output, flush=True)
        if log_path:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write(output)
        if check and proc.returncode != 0:
            raise ConanException(
                f"{shlex.join(command)} failed (rc={proc.returncode})")
        return proc.returncode, output

    def _cargo_with_resource_retry(self, env, subcommand, extra, timeout,
                                   log_path, what):
        rc, output = self._run(self._cargo(env, subcommand, extra), env,
                               timeout, check=False, log_path=log_path)
        if rc != 0 and any(m in output for m in _RESOURCE_EXHAUSTION_MARKERS):
            self.output.warning(
                f"{what}: worker resource exhaustion detected — retrying once "
                "serially (CARGO_BUILD_JOBS=1); cargo resumes incrementally")
            env_serial = dict(env)
            env_serial["CARGO_BUILD_JOBS"] = "1"
            rc, output = self._run(
                self._cargo(env_serial, subcommand, extra), env_serial,
                timeout, check=False, log_path=log_path)
        return rc, output

    # ── build + upstream tests ────────────────────────────────────────

    def build(self):
        cc, _cxx = self._compilers()
        runtime_dirs = self._prepare_cargo_runtime(cc)
        bin_dst, lib_dst = self._prepare_toolchain(runtime_dirs)
        env = self._build_env(bin_dst, lib_dst, runtime_dirs)
        cargo = env["CARGO"]

        # ① Release 构建（单一 CLI bin；LSP 内嵌）。
        rc, _ = self._cargo_with_resource_retry(
            env, "build", ["--release", "--locked", "--bin", BINARY_NAME],
            timeout=10800, log_path=None, what="cargo build")
        if rc != 0:
            raise ConanException(f"cargo build failed (rc={rc})")

        # ② 上游测试（R51）：完整上游套件真实执行（debug，与上游 Makefile
        #    一致；doc-tests 无 rustdoc 用 --tests 排除；平台绑定 crate 排除；
        #    pyo3/Python 绑定 templater 用例按上游官方开关跳过并如实申报）。
        env_tests = dict(env)
        env_tests["SQRUFF_SKIP_UNSUPPORTED_TEMPLATERS"] = "1"
        record = self._run_upstream_tests(env_tests)
        self._persist_upstream_result(record)
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(record), flush=True)
        if record["failed"] != 0:
            raise ConanException(
                "upstream cargo test has failures: "
                + json.dumps(record, ensure_ascii=False))
        if record["passed"] != UPSTREAM_EXPECTED_PASSED:
            raise ConanException(
                "upstream cargo test passed count mismatch: "
                f"{record['passed']} != {UPSTREAM_EXPECTED_PASSED}")

        # ③ 产物 + OHOS 签名。
        target_dir = os.path.join(self.source_folder, "target", "release")
        binary = os.path.join(target_dir, BINARY_NAME)
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                f"cargo did not produce the expected executable: {binary}")
        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        packaged = os.path.join(out_dir, BINARY_NAME)
        shutil.copy2(binary, packaged)
        os.chmod(packaged, 0o755)
        if self.settings.os == "OHOS":
            self._sign([packaged])

    def _run_upstream_tests(self, env):
        logs_dir = os.path.join(self.build_folder, "upstream-test-logs")
        cargo_args = (["--locked", "-j", "4", "--no-fail-fast",
                       "--workspace", "--exclude", "sqruff-cli-python",
                       "--exclude", "sqruff-wasm", "--tests"])
        rc, output = self._cargo_with_resource_retry(
            env, "test", cargo_args, timeout=10800,
            log_path=os.path.join(logs_dir, "workspace.log"),
            what="cargo test (workspace)")
        passed, failed, ignored, filtered = self._parse_test_counts(output)
        for target in _HARNESS_FALSE_TARGETS:
            if ("tests/%s" % target) not in output:
                raise ConanException(
                    "upstream harness=false test target tests/%s did not run "
                    "(cargo output missing its Running line)" % target)
        record = {
            "status": "passed" if (rc == 0 and failed == 0
                                   and passed > 0) else "failed",
            "framework": "cargo",
            "target": OHOS_TARGET,
            "command": ("SQRUFF_SKIP_UNSUPPORTED_TEMPLATERS=1 cargo test "
                        "--locked -j 4 --no-fail-fast --workspace "
                        "--exclude sqruff-cli-python --exclude sqruff-wasm "
                        "--tests"),
            "discovered": passed + failed + filtered,
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "ignored": ignored,
            "filtered_out": filtered,
            "expected_passed": UPSTREAM_EXPECTED_PASSED,
        }
        if rc != 0:
            record["status"] = "failed"
        return record

    @staticmethod
    def _parse_test_counts(output):
        passed = failed = ignored = filtered = 0
        for match in re.finditer(
                r"test result:\s+\w+\.\s+(\d+) passed;\s+(\d+) failed;\s+"
                r"(\d+) ignored(?:;\s+\d+ measured)?(?:;\s+(\d+) filtered out)?",
                output):
            passed += int(match.group(1))
            failed += int(match.group(2))
            ignored += int(match.group(3))
            filtered += int(match.group(4) or 0)
        return passed, failed, ignored, filtered

    def _persist_upstream_result(self, record):
        directory = os.path.join(self.source_folder, "res")
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "upstream_test_result.json"), "w",
                  encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    # ── package ───────────────────────────────────────────────────────

    def package(self):
        copy(self, BINARY_NAME, src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "upstream_test_result.json",
             src=os.path.join(self.source_folder, "res"),
             dst=os.path.join(self.package_folder, "res"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
