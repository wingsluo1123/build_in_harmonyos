#!/usr/bin/env python3
"""Conan recipe — overtls 0.3.12 (cargo / Rust, OHOS).

overtls 是一个极简的 WebSocket over TLS 隧道代理（客户端 SOCKS5 ↔ 本地
WebSocket over TLS ↔ 服务端转发），上游仓库 ShadowsocksR-Live/overtls，
单 crate（`crate-type = ["staticlib","cdylib","lib"]` + `[[bin]] overtls-bin`）。

OHOS 适配要点（本配方实际采用）：
- **Rust 工具链取自仓库内 conan 包 `rust-toolchain/1.97.1`**（`tool_requires`）：
  rust-lang 官方 dist，宿主与目标均为 `aarch64-unknown-linux-ohos`，已发布到仓库
  remote `ohpcd`（2026-10-06 以 `conan list` 与 `conan download` 对 `ohpcd`
  双证 recipe 存在且 `--only-recipe` 可下载；remote 名属 CI 环境配置，配方运行期
  不绑定任何 remote；原始取数命令逐字留痕见 notes.md §6）。
  该包二进制**未带 OHOS code signature**，直接 exec 报 Permission denied（errno 13），
  故复制到构建目录后逐个自签名（`binary-sign-tool`），`rustc` 会 dlopen 的
  `librustc_driver-*.so` 一并签名；rustc 靠自身路径推导 sysroot，搬离包目录会
  E0463，故以 `RUSTFLAGS=--sysroot=<包目录>` 显式指定，~890MB 只读负载留在包内。
  为何不用 harmonybrew 的 rust bottle：`rust-1.97.1` bottle 已 404（实测
  HTTP/1.1 404），与 rainfrog 0.3.20 的结论一致。
- **TLS 面 = rustls + ring（纯 Rust），无 openssl/mbedtls 系统依赖**：上游
  `rustls`/`tokio-rustls` 显式 `default-features=false` + `features=["ring"]`，
  `src/lib.rs` 安装 `rustls::crypto::ring::default_provider()`，`src/tls.rs`
  显式使用 `rustls::crypto::ring::*` 密码套件，WS 握手自实现（`client_async`
  已注释）→ 不引 `openssl-sys`，也不需要 aws-lc-rs。
  **但 `reqwest` 0.13.x 的 `rustls` feature 硬编码 `__rustls-aws-lc-rs`**，会把
  aws-lc-sys 拖进构建；aws-lc-sys 0.45.0 在 OHOS/aarch64 上不产出 perlasm
  汇编对象（CMake 报 `Neither OHOS_NDK_HOME nor OHOS_SDK_NATIVE are set`），
  链接期 200+ 个 `aws_lc_0_45_0_*` 符号未定义 → 配方以
  `patches/0001-Cargo.toml-reqwest-rustls-no-provider.patch` 把 reqwest 改成
  `rustls-no-provider`，全树只剩 ring（`cargo tree -i aws-lc-rs` 无命中）。
  （唯一用到 OpenSSL 的是 cargo 自身的运行期动态库，见 `_fetch_runtime_libs`。）
- **cargo 运行期库**：`rust-toolchain` 的 cargo 动态链接 libssl/libcrypto/libz
  （实测 NEEDED），故仍需 Harmonybrew bottle（URL 实测 HTTP 200）。
- **crate 下载走 rsproxy.cn sparse 镜像**：设备与 CI worker 的 crates.io TLS
  不可达（无 CA bundle），`.cargo/config.toml` 追加 `[source.crates-io]` 替换段，
  并放宽网络容错（retry=10 / timeout=600 / low-speed-limit=1）。
- **OHOS `/tmp` 只读** → `TMPDIR/TMP/TEMP` 指到构建目录下可写目录。
- **上游 tarball 无 `Cargo.lock`**（上游 `.gitignore` 忽略）→ 不能用 `--locked`，
  依赖解析由 rsproxy 实时完成；该事实写入 notes.md 与 PR 正文。

测试：`build()` 内真实执行 `cargo test --release --lib`，以
`HMBS_UPSTREAM_TEST_RESULT` marker 输出客观计数（上游测试是 `src/` 内联
`#[test]`，无顶层 `tests/` 目录）。消费者侧由 `test_package/` 承担。
"""
import glob
import json
import os
import re
import shutil
import subprocess
from urllib.parse import unquote

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


CARGO_BUILD_ARGS = ("build", "--release")
CARGO_TEST_ARGS = ("test", "--release", "--lib")
UPSTREAM_TEST_COMMAND = "cargo " + " ".join(CARGO_TEST_ARGS)

SIGNER_CANDIDATES = (
    "/data/service/hnp/bin/binary-sign-tool",
    "binary-sign-tool",
)

# 追加进上游 `.cargo/config.toml` 的段落（追加而非覆盖：保留上游的 mips/ios
# 链接器设置）。`CRATES_MIRROR_MARK` 同时充当幂等标记。
CRATES_MIRROR_MARK = "# overtls-recipe: crates mirror"
CRATES_MIRROR_BLOCK = (
    "\n" + CRATES_MIRROR_MARK + "\n"
    "[source.crates-io]\n"
    'replace-with = "rsproxy-sparse"\n'
    "\n[source.rsproxy-sparse]\n"
    'registry = "sparse+https://rsproxy.cn/index/"\n'
    "\n[net]\n"
    "retry = 10\n"
    "\n[http]\n"
    "timeout = 600\n"
    "low-speed-limit = 1\n"
)


class OvertlsConan(ConanFile):
    name = "overtls"
    version = "0.3.12"
    description = (
        "overtls — a minimalist WebSocket over TLS proxy tunnel "
        "(SOCKS5 client ↔ ws/wss tunnel ↔ forward server)"
    )
    license = "MIT"
    homepage = "https://github.com/ShadowsocksR-Live/overtls"
    url = "https://github.com/ShadowsocksR-Live/overtls"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "overtls is supported on Linux and OHOS"
            )

    def build_requirements(self):
        # 仓库内工具链包（rust-lang 官方 dist + OHOS aarch64 宿主/目标标准库）。
        # 见模块 docstring：相对 harmonybrew rust bottle（已 404），它随制品仓固定、
        # 不依赖外部 CDN。
        self.tool_requires("rust-toolchain/1.97.1")

    def source(self):
        # filename 由 conandata.yml 的 `sources.filename` 提供，这里不再重复传
        # （重复传会 TypeError: got multiple values for keyword argument）。
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── 工具可用性探测 ────────────────────────────────────────────────
    @staticmethod
    def _runnable(path, expected_name):
        """用**实际执行**判定工具是否可用，绝不用 os.access。

        OHOS 上权限位与"能否 exec"不等价：本机 /usr/local/bin/cargo 是
        0o750、组 file_manager，os.access(X_OK) 返回 True，但 exec 实际报
        Permission denied —— 照抄 os.access 会让构建当场崩在 PermissionError，
        而不会退到工具链供给路径。
        """
        if not path or not os.path.isfile(path):
            return False
        try:
            proc = subprocess.run(
                [path, "--version"], capture_output=True, text=True, timeout=60
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return proc.returncode == 0 and expected_name in (
            (proc.stdout or "") + (proc.stderr or "")
        )

    @staticmethod
    def _find_tool(name):
        """在系统/常见位置找"真能跑"的 cargo/rustc（找不到就供给）。"""
        patterns = [
            "/storage/Users/currentUser/usr/"
            f"rust-*-aarch64-unknown-linux-ohos/bin/{name}",
            os.path.expanduser(
                f"~/usr/rust-*-aarch64-unknown-linux-ohos/bin/{name}"
            ),
        ]
        candidates = []
        for pattern in patterns:
            candidates.extend(glob.glob(pattern))

        def rust_version(path):
            m = re.search(r"/rust-([0-9]+(?:\.[0-9]+)*)-", path)
            return tuple(int(p) for p in m.group(1).split(".")) if m else ()

        candidates.sort(key=rust_version, reverse=True)
        candidates += [
            shutil.which(name),
            os.environ.get(name.upper()),
            os.environ.get(f"HNP_{name.upper()}"),
            f"/data/service/hnp/bin/{name}",
            os.path.expanduser(f"~/.harmonybrew/bin/{name}"),
        ]
        for c in candidates:
            if OvertlsConan._runnable(c, name):
                return c
        return None

    # ── 从 conan 工具包取工具链并自签名 ──────────────────────────────
    @staticmethod
    def _find_signer():
        for cand in SIGNER_CANDIDATES:
            if os.path.isabs(cand):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
            else:
                found = shutil.which(cand)
                if found:
                    return found
        return None

    def _sign(self, path, signer):
        """就地自签名：先写 .signed 再 os.replace，避免签名过程把原文件截断。"""
        tmp = path + ".signed"
        proc = subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", tmp, "-selfSign", "1"],
            capture_output=True, text=True, timeout=600,
        )
        if proc.returncode != 0 or not os.path.isfile(tmp):
            raise ConanException(
                f"failed to sign {path}: {(proc.stdout or '') + (proc.stderr or '')}"
            )
        os.replace(tmp, path)
        os.chmod(path, 0o755)

    def _provision_toolchain(self):
        """从 tool_requires 的 `rust-toolchain` 包取出可执行的 cargo/rustc。

        rust-lang 官方 dist 的二进制**不带 OHOS code signature**，在本设备/CI 上
        直接 exec 报 `Permission denied`（errno 13，与 mode 位和路径无关）；
        故复制到构建目录后逐个自签名。`rustc` 还会 dlopen
        `librustc_driver-*.so`，该库也须一并签名。
        """
        pkg = self.dependencies.build["rust-toolchain"].package_folder
        # rustc 靠自身路径推导 sysroot，二进制一旦搬离包目录就找不到 target 标准库
        # （实测 E0463 can't find crate for `std`）。故记下包目录作为显式 sysroot。
        self._rust_sysroot = pkg
        src_bin = os.path.join(pkg, "bin")
        src_lib = os.path.join(pkg, "lib")
        dest = os.path.join(self.build_folder, "rust-toolchain")
        os.makedirs(os.path.join(dest, "bin"), exist_ok=True)
        os.makedirs(os.path.join(dest, "lib"), exist_ok=True)

        signer = self._find_signer()
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool not found; it is required to sign the "
                "unsigned rust-toolchain binaries on OHOS "
                f"(looked for: {', '.join(SIGNER_CANDIDATES)})"
            )

        targets = []
        for name in ("cargo", "rustc"):
            s = os.path.join(src_bin, name)
            if os.path.isfile(s):
                d = os.path.join(dest, "bin", name)
                shutil.copy2(s, d)
                targets.append(d)
        for drv in glob.glob(os.path.join(src_lib, "librustc_driver-*.so")):
            d = os.path.join(dest, "lib", os.path.basename(drv))
            shutil.copy2(drv, d)
            targets.append(d)
        if not targets:
            raise ConanInvalidConfiguration(
                f"rust-toolchain package has no cargo/rustc under {src_bin}"
            )
        for t in targets:
            self._sign(t, signer)
            self.output.info(f"signed {os.path.relpath(t, dest)}")

        cargo = os.path.join(dest, "bin", "cargo")
        rustc = os.path.join(dest, "bin", "rustc")
        if not (OvertlsConan._runnable(cargo, "cargo")
                and OvertlsConan._runnable(rustc, "rustc")):
            raise ConanInvalidConfiguration(
                "signed rust-toolchain binaries are still not runnable"
            )
        return cargo, rustc

    # ── 运行期库（cargo 动态链接 libssl/libcrypto/libz）──────────────
    @staticmethod
    def _materialize_predl_alias(url):
        """兼容 CI 预下载器对含 `%XX` 文件名的 `file://` 改写。

        `ci/conan/build_and_test.sh` 的 pre-download 段把 conandata.yml 里的 URL 原地改写成
        `file://<predl_dir>/<md5(url)[:8]>_<URL 末段>`，其中 URL 末段**保留百分号编码**；
        而 conan 打开 `file://` 时会对路径做百分号解码（`%40` → `@`）。于是当末段本身含
        `%XX`（本包 openssl bottle 是 `openssl%403-…`）时，改写出来的字面文件还在、conan
        要找的解码名却不存在 ⇒ `get()` 抛 FileNotFoundError（W3/CI 实测）。

        这里只在「解码名缺失、字面名存在」时把字面文件按解码名补一份（硬链接，失败退回
        拷贝），使 conan 能按其自身口径找到它；文件内容与 sha256 仍由 `get()` 亲自校验，
        完整性判据不降级。非 `file://`（正常 HTTPS 取源）与无 `%XX` 的 URL 一律原样放行，
        故本函数在设备直连路径上是空操作。
        """
        prefix = "file://"
        if not url.startswith(prefix):
            return
        literal = url[len(prefix):]
        decoded = unquote(literal)
        if decoded == literal or os.path.exists(decoded) or not os.path.isfile(literal):
            return
        try:
            os.link(literal, decoded)
        except OSError:
            shutil.copy2(literal, decoded)

    def _fetch_runtime_libs(self):
        """下载 OpenSSL / zlib / 根证书、备好 LD_LIBRARY_PATH 与 SSL_CERT_FILE。

        `rust-toolchain` 的 cargo 动态链接 libssl.so / libcrypto.so / libz.so
        （实测 NEEDED），这三者不在该工具包内。候选集按序尝试，任一成功即返回。
        """
        base = os.path.join(self.build_folder, "rust-libs")
        os.makedirs(base, exist_ok=True)
        last_error = None
        for label, bottles in (
            ("pinned", self.conan_data.get("runtime_libs", [])),
            ("fallback-current", self.conan_data.get("runtime_libs_fallback", [])),
        ):
            if not bottles:
                continue
            try:
                self.output.info(f"provisioning rust runtime libs (candidate: {label})")
                for bottle in bottles:
                    self._materialize_predl_alias(bottle["url"])
                    get(
                        self,
                        url=bottle["url"],
                        sha256=bottle["sha256"],
                        destination=base,
                        keep_permissions=True,
                        strip_root=False,
                    )
                break
            except ConanException as exc:
                last_error = exc
                self.output.warning(
                    f"runtime-libs candidate '{label}' failed ({exc}); trying next"
                )
                continue
        else:
            if last_error is not None:
                raise ConanInvalidConfiguration(
                    "no rust runtime-libs candidate could be provisioned; "
                    f"last error: {last_error}"
                )

        lib_dirs = []
        for root, _dirs, files in os.walk(base):
            if os.path.basename(root) != "lib":
                continue
            if {"libssl.so", "libcrypto.so", "libz.so"} & set(files):
                lib_dirs.append(root)
        for d in lib_dirs:
            for f in os.listdir(d):
                p = os.path.join(d, f)
                if os.path.isfile(p) and not os.path.islink(p):
                    try:
                        os.chmod(p, 0o755)
                    except OSError:
                        pass
        if lib_dirs:
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                lib_dirs + ([existing] if existing else [])
            )
        else:
            self.output.warning(
                "no libssl/libcrypto/libz directory found in runtime bottles"
            )

        if not os.environ.get("SSL_CERT_FILE"):
            for root, _dirs, files in os.walk(base):
                for cert_name in ("cert.pem", "cacert.pem"):
                    cert = os.path.join(root, cert_name)
                    if os.path.isfile(cert):
                        os.environ["SSL_CERT_FILE"] = cert
                        os.environ["CURL_CA_BUNDLE"] = cert
                        break
                if os.environ.get("SSL_CERT_FILE"):
                    break

    # ── 构建环境 ─────────────────────────────────────────────────────
    def _mirror_cargo_config(self):
        """向源码树 `.cargo/config.toml` **追加** crates 镜像段（幂等，不覆盖上游）。"""
        cargo_dir = os.path.join(self.source_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        cfg = os.path.join(cargo_dir, "config.toml")
        try:
            with open(cfg, "r", encoding="utf-8") as fh:
                current = fh.read()
        except OSError:
            current = ""
        if CRATES_MIRROR_MARK in current:
            self.output.info("cargo mirror config already present")
            return
        if not current.endswith("\n"):
            current += "\n"
        with open(cfg, "w", encoding="utf-8") as fh:
            fh.write(current + CRATES_MIRROR_BLOCK)
        self.output.info("cargo mirror config appended (rsproxy sparse)")

    def _build_env(self):
        # 先备运行期库：cargo 需要 libssl/libcrypto/libz，库没就位它起不来，
        # 而"起不起得来"是下面判定工具可用的方式。
        self._fetch_runtime_libs()

        self._rust_sysroot = None
        cargo = self._find_tool("cargo")
        rustc = self._find_tool("rustc")
        if not (cargo and rustc) and str(self.settings.os) == "OHOS":
            self.output.info(
                "no runnable cargo/rustc on this host — provisioning from the "
                "rust-toolchain conan package (signing as needed)"
            )
            cargo, rustc = self._provision_toolchain()
        if not cargo or not rustc:
            raise ConanInvalidConfiguration(
                "Rust/Cargo toolchain is required to build overtls; provision "
                "the OHOS Rust toolchain before conan create"
            )

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}
        )
        cc = compiler_executables.get("c") or (
            shutil.which("clang") or "/data/service/hnp/bin/clang"
        )
        cxx = compiler_executables.get("cpp") or (
            shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        )
        tmpdir = (
            os.environ.get("HMBS_TMPDIR")
            or os.environ.get("TMPDIR")
            or os.path.join(self.build_folder, "tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)

        self._mirror_cargo_config()

        env = dict(os.environ)
        env.update(
            {
                "CARGO": cargo,
                "RUSTC": rustc,
                "CC": cc,
                "CXX": cxx,
                "AR": shutil.which("llvm-ar") or shutil.which("ar")
                or "/data/service/hnp/bin/llvm-ar",
                "RUSTFLAGS": (
                    (f"--sysroot={self._rust_sysroot} " if self._rust_sysroot else "")
                    + f"-C linker={cc}"
                ),
                "CARGO_TARGET_DIR": os.path.join(self.build_folder, "target"),
                "CARGO_NET_RETRY": "10",
                "CARGO_HTTP_TIMEOUT": "600",
                "CARGO_BUILD_JOBS": "1",
                "TMPDIR": tmpdir,
                "TMP": tmpdir,
                "TEMP": tmpdir,
            }
        )
        if not env.get("SSL_CERT_FILE"):
            for ca in (
                "/storage/Users/currentUser/usr/local/ssl/cert.pem",
                "/etc/ssl/certs/cacert.pem",
                "/etc/ssl/cert.pem",
                os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem"),
            ):
                if os.path.isfile(ca):
                    env["SSL_CERT_FILE"] = ca
                    env["CURL_CA_BUNDLE"] = ca
                    break
        tool_dirs = list(dict.fromkeys(
            [os.path.dirname(cargo), os.path.dirname(rustc)]
        ))
        env["PATH"] = os.pathsep.join(tool_dirs + [env.get("PATH", "")])
        return cargo, env

    @staticmethod
    def _parse_test_counts(output):
        passed = failed = ignored = 0
        pattern = re.compile(
            r"test result:\s+\w+\.\s+(\d+) passed;\s+"
            r"(\d+) failed;\s+(\d+) ignored;"
        )
        for m in pattern.finditer(output):
            passed += int(m.group(1))
            failed += int(m.group(2))
            ignored += int(m.group(3))
        return passed, failed, ignored

    def _run_upstream_tests(self, cargo, env):
        proc = subprocess.run(
            [cargo, *CARGO_TEST_ARGS],
            cwd=self.source_folder,
            env=env,
            capture_output=True,
            text=True,
            timeout=3600,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        print(output, flush=True)
        passed, failed, ignored = self._parse_test_counts(output)
        executed = passed + failed
        marker = {
            "status": "passed" if proc.returncode == 0 and failed == 0 else "failed",
            "framework": "cargo-test",
            "command": UPSTREAM_TEST_COMMAND,
            "discovered": executed + ignored,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": ignored,
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker), flush=True)
        if proc.returncode != 0 or failed != 0 or executed == 0:
            raise ConanException(
                "overtls upstream cargo tests failed or produced no results: "
                + json.dumps(marker)
            )

    def build(self):
        apply_conandata_patches(self)
        cargo, env = self._build_env()
        proc = subprocess.run(
            [cargo, *CARGO_BUILD_ARGS],
            cwd=self.source_folder,
            env=env,
            capture_output=True,
            text=True,
            timeout=7200,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        print(output, flush=True)
        if proc.returncode != 0:
            raise ConanException(
                f"cargo build failed with exit code {proc.returncode}"
            )
        self._run_upstream_tests(cargo, env)

    def package(self):
        target_dir = os.path.join(self.build_folder, "target", "release")
        binary = os.path.join(target_dir, "overtls-bin")
        if not os.path.isfile(binary):
            raise ConanException(
                f"overtls-bin not found after cargo build: {binary}"
            )
        copy(
            self,
            "overtls-bin",
            src=target_dir,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # 上游默认配置样例随包分发，供 test_package 与消费者直接参考。
        copy(
            self,
            "config.json",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "overtls"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
