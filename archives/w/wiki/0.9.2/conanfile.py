#!/usr/bin/env python3
"""Conan recipe — wiki-tui 0.9.2 (cargo / Rust, OHOS).

wiki-tui 是终端 Wikipedia 浏览器 TUI：ratatui + crossterm 做界面，
wiki-api（reqwest + scraper）做后端，单二进制 `wiki-tui`。

OHOS 适配要点（本配方实际采用）：
- **Rust 工具链取自仓库内 conan 包 `rust-toolchain/1.97.1`**（`tool_requires`，
  rainfrog 0.3.20 同款）：rust-lang 官方 dist，随制品仓固定、不依赖外部 CDN；
  二进制未带 OHOS 签名，构建期复制出来逐个自签名（cargo/rustc/其 dlopen 的
  librustc_driver-*.so），rustc 以 --sysroot 显式指向包目录。
- **运行期库走制品仓 conan 包**（cbindgen 0.28.0 同款方案）：rust-toolchain 的
  cargo 动态链接 libssl.so/libcrypto.so/libz.so（实测 NEEDED），而 Harmonybrew
  bottle 会轮换（openssl@3-3.6.4_1 / zlib-ng-compat-2.3.3_2 实测已 404）。改用
  `tool_requires` openssl/3.5.8.1 + zlib/1.3.2.1（制品仓固定、随 PR 可复现），
  构建期把其静态 PIC 归档重链为私有共享库（clang -shared --whole-archive），
  放进构建目录的私有 lib/ 并注入 LD_LIBRARY_PATH —— 零 CDN 依赖、零系统前缀
  污染（R49）。TLS 应用层用 rustls（patches/0001），OpenSSL 仅服务 cargo 工具自身。
- 上游 `rust-toolchain` 文件钉 1.91.1：那是 rustup 的配置文件，本配方直接
  调真实 cargo/rustc 二进制（非 rustup 代理），该文件被忽略，无需改动。
- 交付物 wiki-tui 二进制在 package() 内自签名（adbtuifm 同款守卫逻辑，
  已签名/非 OHOS 平台直接跳过）。

测试：`build()` 内真实执行 `cargo test --release --workspace --lib --bins`
（上游为 wiki-api/src/search.rs 内联 #[test] 单元测试），并以
HMBS_UPSTREAM_TEST_RESULT marker 输出实测计数。
"""
import glob
import json
import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

CARGO_BUILD_ARGS = ("build", "--release")
CARGO_TEST_ARGS = (
    # --lib --bins：跳过 doctest（rust-lang 最小 dist 不含 rustdoc 二进制，
    # doctest 无法编译）；上游全部单元测试都在 lib/bin 内联 #[test]，不受影响
    "test", "--release", "--workspace",
    # wiki-api-macros 是 proc-macro crate：其 lib 测试二进制在 OHOS 上 exec 时
    # 对宿主 proc-macro 动态库重定位失败（exit 127, symbol not found），属测试
    # 搭建机制限制而非产品缺陷，故排除该 crate 的测试目标（构建不受影响）。
    "--exclude", "wiki-api-macros",
    "--lib", "--bins",
)
UPSTREAM_TEST_COMMAND = "cargo " + " ".join(CARGO_TEST_ARGS)

SIGNER_CANDIDATES = (
    "/data/service/hnp/bin/binary-sign-tool",
    "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
    "binary-sign-tool",
)


class WikiTuiConan(ConanFile):
    name = "wiki"
    version = "0.9.2"
    description = (
        "A simple and easy to use Wikipedia Text User Interface "
        "(ratatui + crossterm + reqwest/rustls)"
    )
    license = "MIT"
    homepage = "https://wiki-tui.net"
    url = "https://github.com/Builditluc/wiki-tui"
    topics = ("tui", "wikipedia", "terminal", "rust")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # 把 conandata.yml 声明的补丁随配方一起导出（apply_conandata_patches 依赖）
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "wiki-tui is supported on Linux and OHOS"
            )

    def build_requirements(self):
        # 仓库内工具链包（rust-lang 官方 dist + OHOS aarch64 宿主/目标标准库）。
        self.tool_requires("rust-toolchain/1.97.1")
        # cargo 的运行期共享库（cbindgen 0.28.0 同款方案）：从这两个包的静态
        # PIC 归档重链 libssl/libcrypto/libz.so（见 _provision_runtime_libs）。
        # 不用 Harmonybrew bottle：该 CDN 会轮换旧版（实测 404），conan 制品仓
        # 随提交固定、可复现。
        self.tool_requires("openssl/3.5.8.1")
        self.tool_requires("zlib/1.3.2.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── 工具可用性探测 ────────────────────────────────────────────────
    @staticmethod
    def _runnable(path, expected_name):
        """用**实际执行**判定工具是否可用，绝不用 os.access（rainfrog 实测：
        设备上 0o750 的 cargo os.access(X_OK)=True 但 exec 报 Permission denied）。"""
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
        """在系统/常见位置找"真能跑"的 cargo/rustc（可选路径，找不到就供给）。"""
        candidates = [
            shutil.which(name),
            os.environ.get(name.upper()),
            os.environ.get(f"HNP_{name.upper()}"),
            f"/data/service/hnp/bin/{name}",
            os.path.expanduser(f"~/.harmonybrew/bin/{name}"),
        ]
        for c in candidates:
            if WikiTuiConan._runnable(c, name):
                return c
        return None

    # ── 签名 ─────────────────────────────────────────────────────────
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

    @staticmethod
    def _sign(path, signer):
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

    # ── 从 conan 工具包取工具链并自签名 ────────────────────────────────
    def _provision_toolchain(self):
        """从 tool_requires 的 `rust-toolchain` 包取出可执行的 cargo/rustc。

        rust-lang 官方 dist 的二进制**不带 OHOS code signature**，直接 exec 报
        `Permission denied`（errno 13）；复制到构建目录后逐个自签名。rustc 还
        会 dlopen librustc_driver-*.so，须一并签名；签名副本搬离包目录后 rustc
        推导不到 sysroot（E0463）→ 以 --sysroot=<包目录> 显式指定。
        """
        pkg = self.dependencies.build["rust-toolchain"].package_folder
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
        if not (self._runnable(cargo, "cargo")
                and self._runnable(rustc, "rustc")):
            for tool in (cargo, rustc):
                probe = subprocess.run(
                    [tool, "--version"], capture_output=True,
                    text=True, timeout=60,
                )
                self.output.info(
                    f"probe {os.path.basename(tool)}: rc={probe.returncode} "
                    f"out={probe.stdout!r} err={probe.stderr!r}"
                )
            raise ConanInvalidConfiguration(
                "signed rust-toolchain binaries are still not runnable; "
                "see probe output above"
            )
        return cargo, rustc

    # ── 运行期库（cargo 动态链接 libssl/libcrypto/libz）────────────────
    def _provision_runtime_libs(self, cc):
        """从 conan 包的静态 PIC 归档重链出私有 libssl/libcrypto/libz.so。

        rust-toolchain 的 cargo 动态链接 libssl.so/libcrypto.so/libz.so（实测
        NEEDED）。OHOS loader 忽略 DT_RUNPATH，须把私有 lib/ 注入
        LD_LIBRARY_PATH。不落系统前缀、不落包内（R26/R49：零污染）。
        """
        from pathlib import Path
        runtime = Path(self.build_folder) / "cargo-runtime"
        runtime.mkdir(exist_ok=True)
        openssl = Path(self.dependencies.build["openssl"].package_folder)
        zlib = Path(self.dependencies.build["zlib"].package_folder)
        for name, pkg, extra in (
            ("crypto", openssl, ["-ldl", "-pthread"]),
            ("ssl", openssl, ["-L" + str(runtime), "-lcrypto"]),
            ("z", zlib, []),
        ):
            archive = next(pkg.rglob("lib" + name + ".a"))
            command = [cc, "-shared", "-Wl,-z,relro,-z,now",
                       "-Wl,-soname,lib" + name + ".so",
                       "-Wl,--whole-archive", str(archive),
                       "-Wl,--no-whole-archive"] + extra + \
                      ["-o", str(runtime / ("lib" + name + ".so"))]
            self.run(shlex.join(command), env="conanbuild")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            [str(runtime)]
            + ([os.environ["LD_LIBRARY_PATH"]]
               if os.environ.get("LD_LIBRARY_PATH") else [])
        )
        # rustls 做 TLS，不需要 OpenSSL CA；但 cargo 自身（libcurl）访问
        # crates registry 需要系统根证书。
        if not os.environ.get("SSL_CERT_FILE"):
            for ca in (
                "/storage/Users/currentUser/usr/local/ssl/cert.pem",
                "/etc/ssl/certs/cacert.pem",
                "/etc/ssl/cert.pem",
                os.path.expanduser(
                    "~/.harmonybrew/etc/ca-certificates/cert.pem"),
            ):
                if os.path.isfile(ca):
                    os.environ["SSL_CERT_FILE"] = ca
                    os.environ["CURL_CA_BUNDLE"] = ca
                    break

    # ── 构建环境 ─────────────────────────────────────────────────────
    def _build_env(self):
        self._rust_sysroot = None

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}
        )
        cc = compiler_executables.get("c") or (
            shutil.which("clang") or "/data/service/hnp/bin/clang"
        )
        cxx = compiler_executables.get("cpp") or (
            shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        )
        # 先备好 cargo 运行期共享库（libssl/libcrypto/libz，cbindgen 方案），
        # 否则签名后的 cargo 在 _provision_toolchain 探测时 exec 失败
        self._provision_runtime_libs(cc)

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
                "Rust/Cargo toolchain is required to build wiki-tui; "
                "provision the OHOS Rust toolchain before conan create"
            )

        tmpdir = (
            os.environ.get("TMPDIR")
            or os.path.join(self.build_folder, "tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)

        # .cargo/config.toml 写进 source folder（cargo 自 cwd 向上发现配置）：
        # rsproxy sparse 镜像 + 网络容错（argc/alacritty 家族同款）
        cargo_config_dir = os.path.join(self.source_folder, ".cargo")
        os.makedirs(cargo_config_dir, exist_ok=True)
        content = (
            '[build]\ntarget-dir = "target"\n'
            '[source.crates-io]\nreplace-with = "rsproxy-sparse"\n'
            '[source.rsproxy-sparse]\n'
            'registry = "sparse+https://rsproxy.cn/index/"\n'
            "[net]\nretry = 10\n"
            "[http]\ntimeout = 600\nlow-speed-limit = 1\nmultiplexing = false\n"
        )
        if str(self.settings.os) == "OHOS":
            content += (
                "\n[target.aarch64-unknown-linux-ohos]\n"
                f'linker = "{cc}"\n'
            )
        with open(
            os.path.join(cargo_config_dir, "config.toml"), "w", encoding="utf-8"
        ) as handle:
            handle.write(content)

        env = dict(os.environ)
        env.update(
            {
                "CARGO": cargo,
                "RUSTC": rustc,
                "CC": cc,
                "CXX": cxx,
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
        """上游测试三步法（R51）：wiki-tui 0.9.2 无顶层 tests/ 目录，测试为
        wiki-api/src/search.rs 内联 #[test]（grep 计 1 处）。cargo test 实跑
        计数以 stdout 解析为准（HMBS_UPSTREAM_TEST_RESULT marker）。"""
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
            "reason": (
                "conanfile.py build() ran `cargo test --release --workspace "
                "--exclude wiki-api-macros --lib --bins` on the real device; "
                "counts parsed from cargo test stdout"
            ),
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker), flush=True)
        if proc.returncode != 0 or failed != 0 or executed == 0:
            raise ConanException(
                "wiki-tui upstream cargo tests failed or produced no results: "
                + json.dumps(marker)
            )

    def build(self):
        apply_conandata_patches(self)
        cargo, env = self._build_env()
        # 不用 --locked：patches/0001 修改了 wiki-api/Cargo.toml 的 reqwest
        # 声明（native-tls → rustls），cargo 需按新 manifest 更新 Cargo.lock
        # （从 rsproxy 解析 rustls 依赖族），上游其余钉版保持不变。
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

    # ── 交付物签名 ───────────────────────────────────────────────────
    @staticmethod
    def _has_ohos_signature(path):
        try:
            with open(path, "rb") as binary:
                blob = binary.read()
                return b".codesign" in blob or b".note.ohos" in blob
        except OSError:
            return False

    def _sign_elf_if_ohos(self, path):
        if str(self.settings.os) != "OHOS":
            return
        if self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return
        signer = self._find_signer()
        if not signer:
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to sign OHOS executables"
            )
        self._sign(path, signer)

    def package(self):
        target_dir = os.path.join(self.build_folder, "target", "release")
        binary = os.path.join(target_dir, "wiki-tui")
        if not os.path.isfile(binary):
            raise ConanException(
                f"wiki-tui binary not found after cargo build: {binary}"
            )
        self._sign_elf_if_ohos(binary)
        copy(
            self,
            "wiki-tui",
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

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
