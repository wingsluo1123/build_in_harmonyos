#!/usr/bin/env python3
"""Conan test_package for libheif-rav1e 1.23.0（消费者视角 + 上游测试，R34/R51）。

验证三件事：

1. 链接：``find_package(libheif)`` 找到本包交付的宿主（CMakeDeps，目标
   ``libheif::libheif``）；
2. 运行：``LIBHEIF_PLUGIN_PATH`` / ``LD_LIBRARY_PATH`` 由本包 ``package_info()`` 的
   ``runenv_info``（以及 ``cpp_info.libdirs``）经 VirtualRunEnv（``env="conanrun"``）
   带出——前者让宿主找到交付的插件模块；
3. 功能（R34）：宿主 dlopen 交付的 ``libheif-rav1e.so`` 后
   ``heif_have_encoder_for_format(AV1)==1``，并真实编码一张 128x128 AVIF
   （进入 rav1e 编码器）。

此外真跑上游 rav1e 的 ``cargo test``（R51 三步法第 2 步，HMBS 标记），源码从
conandata.yml 声明的官方源重新下载（与包构建同源）。

CI 通过 ``conan create`` 自动执行本测试。
"""
import json
import os
import re
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import get as conan_get

# 内树构建 rav1e 使用的 OHOS 目标三元组（与主配方一致）。
_TARGET = "aarch64-unknown-linux-ohos"
_RUNTIME = "rust-runtime"

# 上游 rav1e 官方源（与 conandata.yml 的 rav1e 键逐字一致；R39 官方源）。
_RAV1E_SOURCES = {
    "url": [
        "https://github.com/xiph/rav1e/archive/refs/tags/v0.7.1.tar.gz",
        "https://codeload.github.com/xiph/rav1e/tar.gz/refs/tags/v0.7.1",
    ],
    "sha256": "da7ae0df2b608e539de5d443c096e109442cdfa6c5e9b4014361211cf61d030c",
    "filename": "rav1e-0.7.1.tar.gz",
}

UPSTREAM_TEST_FRAMEWORK = "cargo-test"
UPSTREAM_TEST_COMMAND = (
    "cargo test --release --workspace --tests --no-fail-fast")


class LibheifRav1eTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # R51：上游 cargo test 需要 Rust 工具链（与主配方同一套 tool_requires）。
        self.tool_requires("rust-toolchain/1.97.1")
        self.tool_requires("openssl/3.5.6.1.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # ---- 消费者视角：宿主装载插件并真实编码（R34）----
        # env="conanrun"：VirtualRunEnv 脚本（含本包 runenv_info 导出的
        # LIBHEIF_PLUGIN_PATH，以及 cpp_info.libdirs 的 LD_LIBRARY_PATH）。
        self.run(
            os.path.join(self.cpp.build.bindirs[0], "test_libheif_rav1e"),
            env="conanrun",
        )

        # ---- 上游 rav1e cargo test（R51，HMBS 标记）----
        if not can_run(self):
            self.output.info("cross-building: upstream cargo test skipped")
            return
        self._run_upstream_tests()

    # --------------------------------------------------------- Rust 运行时准备
    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        return compilers.get("c") or os.environ.get("CC") or "clang"

    def _sign_tool(self):
        cc = self._cc()
        for candidate in (os.path.join(os.path.dirname(cc), "binary-sign-tool"),
                          os.environ.get("BINARY_SIGN_TOOL"),
                          "/data/service/hnp/bin/binary-sign-tool"):
            if candidate and os.path.isfile(candidate):
                return candidate
        import shutil
        return shutil.which("binary-sign-tool")

    def _sign_copy(self, sign_tool, src, dst):
        tmp = dst + ".signed"
        result = subprocess.run(
            [sign_tool, "sign", "-inFile", src, "-outFile", tmp,
             "-selfSign", "1"], capture_output=True, timeout=300)
        if result.returncode or not os.path.isfile(tmp):
            raise ConanException(
                "signing %s failed: %s" % (
                    src, result.stderr.decode(errors="replace")[-2000:]))
        os.replace(tmp, dst)
        os.chmod(dst, 0o755)

    def _prepare_rust_runtime(self):
        """与主配方同款：签名私有拷贝 + openssl relink（rust-rav1e 权威手法）。"""
        from pathlib import Path
        rust = Path(self.dependencies.build["rust-toolchain"].package_folder)
        openssl = Path(self.dependencies.build["openssl"].package_folder)
        runtime = Path(self.build_folder) / _RUNTIME
        (runtime / "bin").mkdir(parents=True, exist_ok=True)
        (runtime / "lib").mkdir(exist_ok=True)
        cc = self._cc()
        sign_tool = self._sign_tool()

        for name in ("crypto", "ssl"):
            dst = runtime / "lib" / f"lib{name}.so"
            if dst.is_file():
                continue
            archives = [str(p) for p in openssl.rglob(f"lib{name}.a")]
            if not archives:
                raise ConanException(f"lib{name}.a not found in openssl package")
            cmd = [cc, "-shared", "-Wl,-z,relro,-z,now",
                   f"-Wl,-soname,lib{name}.so",
                   "-Wl,--whole-archive", archives[0],
                   "-Wl,--no-whole-archive", "-ldl", "-pthread"]
            if name == "ssl":
                cmd += [f"-L{runtime / 'lib'}", "-lcrypto"]
            cmd += ["-o", str(dst)]
            subprocess.run(cmd, check=True, capture_output=True, timeout=300)

        cargo = runtime / "bin" / "cargo"
        rustc = runtime / "bin" / "rustc"
        if not (cargo.is_file() and rustc.is_file()):
            if sign_tool is None:
                pkg_cargo = rust / "bin" / "cargo"
                pkg_rustc = rust / "bin" / "rustc"
                if os.access(pkg_cargo, os.X_OK) and os.access(pkg_rustc, os.X_OK):
                    return (str(pkg_cargo.resolve()), str(pkg_rustc.resolve()))
                raise ConanException(
                    "binary-sign-tool unavailable; rust binaries not executable")
            for tool in ("cargo", "rustc"):
                self._sign_copy(sign_tool, str(rust / "bin" / tool),
                                str(runtime / "bin" / tool))
            for driver in (rust / "lib").glob("librustc_driver*.so"):
                dst = runtime / "lib" / driver.name
                if not dst.is_file():
                    self._sign_copy(sign_tool, str(driver), str(dst))
            libcxx = runtime / "lib" / "libc++_shared.so"
            if not libcxx.is_file():
                source = next(
                    (p for p in ("/system/lib64/libc++_shared.so",
                                 "/usr/lib/libc++_shared.so")
                     if os.path.isfile(p)), None)
                if source:
                    self._sign_copy(sign_tool, source, str(libcxx))
        rustlib = runtime / "lib" / "rustlib"
        if not rustlib.exists():
            rustlib.symlink_to(rust / "lib" / "rustlib", target_is_directory=True)
        return (str(cargo.resolve()), str(rustc.resolve()))

    def _run_upstream_tests(self):
        """真跑上游 rav1e 的 cargo test（R51 三步法第 2 步）。"""
        import certifi
        cargo, rustc = self._prepare_rust_runtime()
        cc = self._cc()

        cargo_home = os.path.join(self.build_folder, "cargo-home")
        os.makedirs(cargo_home, exist_ok=True)
        ca = certifi.where()
        with open(os.path.join(cargo_home, "config.toml"), "w",
                  encoding="utf-8") as f:
            f.write(
                '[source.crates-io]\n'
                'replace-with = "rsproxy-sparse"\n'
                '[source.rsproxy-sparse]\n'
                'registry = "sparse+https://rsproxy.cn/index/"\n'
                '[net]\nretry = 10\n'
                '[http]\ntimeout = 600\n'
                f'cainfo = "{ca}"\n'
                f'\n[target.{_TARGET}]\nlinker = "{cc}"\n')

        # 源码从 conandata.yml 声明的官方源重新下载（与包构建同源）。先尝试读
        # 父版本目录的 conandata.yml；读不到则用本文件内与之逐字一致的常量。
        src_root = os.path.join(self.build_folder, "src-upstream")
        os.makedirs(src_root, exist_ok=True)
        sources = _RAV1E_SOURCES
        try:
            import yaml
            version_dir = os.path.dirname(self.recipe_folder)
            with open(os.path.join(version_dir, "conandata.yml"),
                      encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data.get("rav1e", {}).get("sha256"):
                sources = data["rav1e"]
        except Exception as exc:  # noqa: BLE001 - 回退到内置常量
            self.output.info(f"conandata.yml unavailable ({exc}); using builtin sources")
        conan_get(self, **sources, strip_root=True, destination=src_root)

        runtime = os.path.join(self.build_folder, _RUNTIME)
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = dict(os.environ)
        env.update({
            "CARGO": cargo,
            "RUSTC": rustc,
            "RUSTDOC": rustc,  # built 0.7.1 探测；minimal 工具链无 rustdoc
            "CC": cc,
            "RUSTFLAGS": f"-C linker={cc} -C relocation-model=pic",
            "CARGO_HOME": cargo_home,
            "CARGO_TARGET_DIR": os.path.join(self.build_folder, "target"),
            # 与主配方同口径：单线程。HMDFS 上并发跑 Rust build script 会触发
            # "Text file busy (os error 26)"（写出的 build script 立刻被 exec，
            # 多 crate 并行时同一文件上出现写/执行竞争）。见主配方 _build_rav1e()。
            "CARGO_BUILD_JOBS": "1",
            "CARGO_NET_RETRY": "10",
            "CARGO_HTTP_TIMEOUT": "600",
            "CARGO_HTTP_CAINFO": ca,
            "SSL_CERT_FILE": ca,
            "TMPDIR": tmpdir,
            "LD_LIBRARY_PATH": os.pathsep.join([
                os.path.join(runtime, "lib"), runtime,
                env.get("LD_LIBRARY_PATH", ""),
            ]),
            "PATH": os.pathsep.join([
                os.path.dirname(cargo), env.get("PATH", ""),
            ]),
        })

        # -j 1：单线程，规避 HMDFS 并发 build script 的 "Text file busy"（同主配方）。
        test_args = [cargo, "test", "-j", "1", "--release", "--workspace", "--tests",
                     "--no-fail-fast", "--target", _TARGET]
        print(f"running upstream tests: {' '.join(test_args)}", flush=True)
        proc = subprocess.run(test_args, capture_output=True, text=True,
                              cwd=src_root, env=env, timeout=7200)
        output = (proc.stdout or "") + (proc.stderr or "")
        print(output, flush=True)

        result_lines = re.findall(
            r"test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;"
            r" (\d+) measured; (\d+) filtered out",
            output)
        passed = sum(int(n) for _, n, _, _, _, _ in result_lines)
        failed = sum(int(n) for _, _, n, _, _, _ in result_lines)
        ignored = sum(int(n) for _, _, _, n, _, _ in result_lines)
        executed = passed + failed
        status = ("passed"
                  if (proc.returncode == 0 and failed == 0 and executed > 0)
                  else "failed")
        marker = {
            "status": status,
            "framework": UPSTREAM_TEST_FRAMEWORK,
            "command": " ".join(shlex.quote(p) for p in test_args),
            "discovered": executed + ignored,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": ignored,
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(marker)}")
        if status != "passed":
            raise ConanException(
                f"upstream cargo test failed (rc={proc.returncode}, "
                f"passed={passed}, failed={failed})")
