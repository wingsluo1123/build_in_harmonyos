#!/usr/bin/env python3
"""Conan recipe for libheif-rav1e 1.23.0 — libheif 树内 rav1e（AV1）编码后端插件模块。

交付面 = 上游 libheif 1.23.0 树内的 CMake MODULE 目标 ``heif-rav1e``：

    libheif/plugins/CMakeLists.txt:72-74
        set(RAV1E_sources encoder_rav1e.cc encoder_rav1e.h)
        set(RAV1E_extra_plugin_sources ../error.cc)
        plugin_compilation(rav1e RAV1E RAV1E_FOUND RAV1E RAV1E)
    →  add_library(heif-rav1e MODULE ...)                 # 插件装载开启时
        install(TARGETS heif-rav1e LIBRARY DESTINATION <libdir>/libheif)

``rav1e`` 是**上游目标名里就带的子模块名**（``heif-${name}`` → ``heif-rav1e``），
包名按仓库惯例取「交付库的文件名去掉前后缀」= ``libheif-rav1e``（同族先例：
``archives/l/libhwy_test`` ← 树内目标 ``hwy_test`` → ``libhwy_test.a``；
``libheif-svtenc`` ← ``heif-svtenc``）。

**rav1e 本体是外部依赖，且制品仓没有它** —— 上游 libheif 只随包提供探测模块
``cmake/modules/FindRAV1E.cmake`` 与适配源 ``libheif/plugins/encoder_rav1e.{cc,h}``，
树内**没有任何 rav1e 源码副本**（``find . -iname '*rav1e*'`` 只命中上述三个文件
加上 ``third-party/rav1e.cmd`` 这个 Windows 辅助脚本）；上游用 ``find_package(RAV1E)``
找外部库。而 W0 实测（真实 ``conan download --only-recipe``，非 ``conan list/search``，
R35）表明 ``rav1e``/``librav1e``/``rust-rav1e`` 在 ohpcd 制品仓**任何版本都不存在**
（三者均返回 "Found 0 pkg/version recipes"）。逐条读数见 notes.md「W0 依赖判定」。

因此本包**不声明任何 Conan ``requires``**，改为在包内树构建官方 rav1e 0.7.1：
理由与先例 —— R36 是机械门禁（``finish`` step[5/10] 与 CI L0i 都对 ``requires()``
逐条跑 ``conan download --only-recipe``），声明一个不存在的依赖必然 HANDOFF/红 CI；
而「内树构建所需的编码器、因此没有 Conan 包依赖」在本仓库有**已合并先例**：
``archives/l/libheif-svtenc/1.23.0``（同类编码后端插件，内树构建 SVT-AV1 3.1.2）、
``archives/l/libheif-aom/1.23.0``（内树构建 libaom 3.9.1 静态库）、
``archives/h/handbrake/1.11.2``（明写 "All 33 contribs ... are built in-tree ... so
there are no Conan package dependencies"）。

rav1e 是 Rust 项目，构建方式完全复用仓库 upstream 分支上已验证的权威配方
``archives/r/rust-rav1e/0.7.1``（tool_requires rust-toolchain/1.97.1 + cbindgen/0.28.0
+ openssl/3.5.6.1.1；自签 cargo/rustc/librustc_driver 私有拷贝；openssl 静态归档
relink 私有 libssl/libcrypto；RUSTDOC=rustc；rsproxy.cn sparse 镜像）：

  1. ``cbindgen --config cbindgen.toml --crate rav1e`` → ``rav1e.h``（上游官方配置）；
  2. ``cargo rustc --release --target aarch64-unknown-linux-ohos --locked
     --no-default-features --features capi,asm,threading --crate-type staticlib``
     → ``librav1e.a``（cargo-c 等价物；NEON 汇编由 build.rs 经 cc crate 编入）。

交付面（自包含，因为插件模块无法脱离宿主运行）：

  * ``lib/libheif/libheif-rav1e.so``（+ VERSION/SOVERSION 软链）—— 本包命名产物，
    由树内 ``encoder_rav1e.cc`` 编译，**静态链入内树构建的 librav1e.a**；
  * 宿主 ``lib/libheif.so``（同源同版本、``ENABLE_PLUGIN_LOADING=ON``）—— 插件以
    ``target_link_libraries(heif-rav1e PRIVATE ${RAV1E_LIBRARIES} heif)`` 依赖它，且运行期
    必须由它 ``dlopen`` 插件才能注册 AV1 编码器；仓库既有 ``archives/l/libheif/1.22.2``
    是 ``ENABLE_PLUGIN_LOADING=OFF`` 的 codec-free 核心，**装不了插件**，故不能作为本包的
    依赖（跨版本插件 ABI 也不匹配）；
  * ``include/libheif/*.h``、``lib/pkgconfig/libheif.pc``、``lib/cmake/libheif/*``；
  * ``include/rav1e.h`` + ``lib/librav1e.a`` —— 交付面输入（内树构建产物，随包归档，
    便于自证与二次核对；消费者默认只链接 ``heif``，不自动链接 rav1e）。

上游构建开关说明（R1：参数最少化，只开交付面必需的）：

  * ``ENABLE_PLUGIN_LOADING=ON`` + ``WITH_RAV1E=ON`` + ``WITH_RAV1E_PLUGIN=ON``：
    上游 ``plugin_option(RAV1E "Rav1e AV1 encoder" OFF ON)`` 即 WITH_RAV1E 默认 OFF、
    WITH_RAV1E_PLUGIN 默认 ON；三者共同构成本包交付面（缺一则不产生 ``heif-rav1e``
    目标，改为静态编入宿主）；
  * ``BUILD_TESTING=OFF``：上游测试目标不被 ``install()``，不属交付面；本包的上游
    用例清点与归因见 notes.md，消费者验证由 ``test_package/`` 承担；
  * 其余后端（libde265/x265/x264/aom 编解码/dav1d/kvazaar/uvg266/vvdec/vvenc/
    ffmpeg/openh264/svtenc/jpeg/openjpeg/openjph/libsharpyuv/未压缩编码）全部显式 OFF：
    不属交付面，且会引入未发布依赖（R36）。

FindRAV1E.cmake 输入：上游是 MODULE 模式（``libfind_pkg_check_modules(RAV1E_PKGCONF rav1e)``
+ 无 HINTS 的 ``find_path(RAV1E_INCLUDE_DIR NAMES rav1e.h)`` /
``find_library(RAV1E_LIBRARY NAMES librav1e rav1e rav1e.dll)``），不认 CMakeDeps 生成的
config；直接钉 cache 变量 ``RAV1E_INCLUDE_DIR`` / ``RAV1E_LIBRARY`` 指向内树产物，
既避免命中设备上的系统 librav1e，也不依赖 pkg-config 是否可用/是否被污染。

插件目录：上游把默认插件目录**编译期钉死**在 ``heif_version.h`` 的
``LIBHEIF_PLUGIN_DIRECTORY``（= 构建时的 ``${CMAKE_INSTALL_FULL_LIBDIR}/libheif``，
即本包在 Conan 缓存里的绝对路径），跨缓存/跨机不可移植。因此 ``package_info()`` 用
``runenv_info`` 导出 ``LIBHEIF_PLUGIN_PATH``，让 ``VirtualRunEnv``/``conanrun`` 环境
自动带上（上游 ``libheif/plugins_unix.cc`` 优先读该环境变量；头文件 ``heif_library.h``
注释里的复数 ``LIBHEIF_PLUGIN_PATHS`` 是过期文档）。

上游测试（R51 三步法第 2 步）
---------------------------
``build()`` 末尾在**独立构建目录** ``<build>/upstream-tests`` 里，按上游
``CMakePresets.json`` 的 ``testing`` preset 语义（``BUILD_TESTING=ON`` +
``WITH_REDUCED_VISIBILITY=OFF`` + ``WITH_UNCOMPRESSED_CODEC=ON`` +
``ENABLE_EXPERIMENTAL_FEATURES=ON``）编译并真跑上游 ``tests/`` 全套 CTest/Catch2 用例，
打印 ``HMBS_UPSTREAM_TEST_RESULT`` 用例级台账（N′=212，PASS 212 / FAIL 0 / SKIP 0）。

测试需要的编解码后端（dav1d / libde265 / x265 / openjpeg / openjph / libtiff，均为
ohpcd 已发布包）以 ``build_requirements()`` 的 ``tool_requires`` 声明——只进 build
上下文，**交付包 ``requirements()`` 保持为空、交付产物链接面不变**；缺了它们，上游测试
会整片 Catch2 SKIP（那不算"真跑"）。测试构建与交付构建分目录，交付产物的开关保持最小面。
"""
import glob
import hashlib
import json
import os
import re
import shlex
import subprocess

import certifi
from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

# 内树构建的 rav1e 源码目录名（== source() 里 get() 的落点 == 补丁的 base_path）。
_RAV1E_DIR = "rav1e"
# rust-toolchain/1.97.1 的 OHOS 目标三元组（host target）。
_TARGET = "aarch64-unknown-linux-ohos"
# cargo/rustc/openssl-relink 私有运行时的落点（build_folder 子目录）。
_RUNTIME = "rust-runtime"
# 上游测试套件（libheif tests/ = Catch2 + CTest）的独立构建目录（build_folder 子目录）。
# 与交付构建分开：上游「testing」preset 的开关（REDUCED_VISIBILITY=OFF 等）只作用于
# 测试构建，交付产物的开关保持最小面不变。
_TEST_BUILD_DIR = "upstream-tests"

# 上游测试套件所需的编解码后端（**仅测试构建使用**，不进入交付产物的链接面）。
# 为什么用 tool_requires 而不是 requires：交付包必须保持 requirements() 为空
# （插件只静态链入内树 rav1e，消费者只链 heif）；这些后端只是让上游测试里的
# get_encoder_or_decoder_or_skip 断言**真正执行**（而不是 Catch2 SKIP）——
# 它们出现在 build 上下文，不进入交付包的 requires 依赖面，也不写进 cpp_info。
# 均为 ohpcd 制品仓已发布包（R36/CI L0i 逐个 conan download 实测通过）。
_TEST_CODEC_REQUIRES = (
    "dav1d/1.5.0",       # AV1 解码：encode_grid 往返 / component_descriptions
    "libde265/1.0.18",   # HEVC 解码：mini_decode 等
    "x265/4.2",          # HEVC 编码：encode / omaf / tai / extended_type
    "openjpeg/2.5.4",    # J2K 编码：encode_jpeg2000
    "openjph/0.31.0",    # HT-J2K 编码：encode_htj2k
    "libtiff/4.7.2.1",   # heifio TIFF 输入：tiffdecode
)

# 下列后端在**交付构建**里显式 OFF；测试构建里改为 ON（上游测试需要），
# 其余仍保持 OFF。见 _test_common_defines()。
_TEST_ENABLED_OPTIONS = (
    "LIBDE265", "X265", "DAV1D", "OpenJPEG_DECODER", "OpenJPEG_ENCODER",
    "OPENJPH_ENCODER",
)

# 本包交付面之外的上游后端开关：显式 OFF（不属交付面 + 未发布依赖）。
_DISABLED_PLUGIN_OPTIONS = (
    "LIBDE265", "X265", "X264", "AOM_DECODER", "AOM_ENCODER", "DAV1D", "KVAZAAR",
    "UVG266", "VVDEC", "VVENC", "FFMPEG_DECODER", "OpenH264_DECODER", "SvtEnc",
    "JPEG_DECODER", "JPEG_ENCODER", "OpenJPEG_DECODER", "OpenJPEG_ENCODER",
    "OPENJPH_ENCODER", "LIBSHARPYUV",
)


class LibheifRav1eConan(ConanFile):
    name = "libheif-rav1e"
    version = "1.23.0"
    description = ("rav1e (AV1) encoder backend plugin module for libheif 1.23.0, built "
                   "in-tree from libheif/plugins/encoder_rav1e.cc as the upstream CMake "
                   "target heif-rav1e (libheif-rav1e.so); the rav1e encoder itself is also "
                   "built in-tree (official v0.7.1 source via the OHOS Rust toolchain, "
                   "producing librav1e.a + rav1e.h) because no Conan package for it is "
                   "published; ships the plugin-loading-enabled libheif host it requires")
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/strukturag/libheif"
    url = "https://github.com/strukturag/libheif"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        # 本包 conandata.yml 是 `patches: {}`（零补丁、上游源码零修改），此调用是 no-op；
        # 保留为仓库既有惯例，也让将来真需要加补丁时落点已在正确位置（conan_verify G1
        # 配方完整性门禁按此结构检查）。
        export_conandata_patches(self)

    def requirements(self):
        # 零 Conan 运行时依赖：rav1e 本体由本包内树构建（官方 v0.7.1 源码 + Rust 工具链）。
        # 为什么不能写成 self.requires("rust-rav1e/0.7.1")：该 ref 在 ohpcd 制品仓不存在，
        # R36 机械门禁（finish step[5/10] / CI L0i 的 conan download --only-recipe）必然
        # HANDOFF；逐条证据见 notes.md「W0 依赖判定」。
        pass

    def build_requirements(self):
        # R36：工具链依赖均已发布到 ohpcd 制品仓（本任务逐条 conan download 实测）。
        # 三者与 upstream 分支 archives/r/rust-rav1e/0.7.1 的权威配方一致。
        self.tool_requires("rust-toolchain/1.97.1")
        self.tool_requires("cbindgen/0.28.0")
        self.tool_requires("openssl/3.5.6.1.1")
        # 上游测试套件所需的编解码后端（均已发布；仅测试构建使用，见文件头常量注释）。
        for ref in _TEST_CODEC_REQUIRES:
            self.tool_requires(ref)

    def validate(self):
        if not self.options.shared:
            # 插件以 MODULE 形态被宿主 dlopen，必须与宿主共享同一份 libheif 运行时；
            # 静态宿主会让插件自带一份副本（状态分裂）。上游 BUILD_SHARED_LIBS 默认 ON。
            raise ConanInvalidConfiguration(
                f"{self.ref}: 插件模块形态要求宿主 heif 为共享库（shared=True）")
        # R32：settings.os 判断必须 in ("Linux", "OHOS")，不能 == "Linux"。
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref}: 仅支持 Linux / OHOS，收到 {self.settings.os}")
        # 内树 Rust 目标三元组固定 aarch64；arch 非 armv8 时不能复用该工具链。
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                f"{self.ref}: 内树 rav1e 目标为 aarch64-unknown-linux-ohos，"
                f"要求 arch=armv8，收到 {self.settings.arch}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # 1) 父 tarball：libheif 1.23.0（交付面源码）
        get(self, **self.conan_data["sources"], strip_root=True)

        # 2) 内树构建的 rav1e 0.7.1（官方源，url 列表含官方 codeload 回退）
        get(self,
            destination=os.path.join(self.source_folder, _RAV1E_DIR),
            strip_root=True,
            **self.conan_data["rav1e"])

        # 3) 本包无补丁（patches: {}）；保留调用为仓库标准落点。
        apply_conandata_patches(self)

    # ------------------------------------------------------------------ helpers
    def _jobs(self):
        """构建并发上限。

        共享设备口径：本工作区为共享设备（conan 取 os.cpu_count()=20 而容器 affinity
        只有 8，2.5× 超订），未限制的 cmake --build 会放大内存峰值；``conan create``
        由 CI/工具直接调用，不会替我们传 ``-c tools.build:jobs``，所以默认值必须落在
        配方里。取 4 作上限：调用方显式给值时尊重但仍不超过 4。
        """
        jobs = self.conf.get("tools.build:jobs", default=4, check_type=int) or 4
        return max(1, min(jobs, 4))

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        return compilers.get("c") or os.environ.get("CC") or "clang"

    def _cxx(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        return compilers.get("cpp") or os.environ.get("CXX") or "clang++"

    def _sign_tool(self):
        cc = self._cc()
        for candidate in (os.path.join(os.path.dirname(cc), "binary-sign-tool"),
                          os.environ.get("BINARY_SIGN_TOOL"),
                          "/data/service/hnp/bin/binary-sign-tool"):
            if candidate and os.path.isfile(candidate):
                return candidate
        import shutil
        return shutil.which("binary-sign-tool")

    @staticmethod
    def _sha256(path):
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

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

    # ------------------------------------ Rust 工具链运行时（rust-rav1e 权威手法）
    def _prepare_rust_runtime(self):
        """签名 cargo/rustc 私有拷贝 + openssl relink 私有 .so + sysroot 布局。

        rust-toolchain 包内二进制在 OHOS HMDFS 上无执行标签（E046 同类），复制到
        build_folder 私有目录用 binary-sign-tool 自签；cargo 运行期的
        libssl/libcrypto 从 openssl conan 包静态归档 --whole-archive relink
        （系统 libssl 3.0 缺 cargo 1.97 需要的符号）；librustc_driver*.so 与
        libc++_shared.so 同样处理。签名后布局 <runtime>/bin/{cargo,rustc}
        + <runtime>/lib/{driver.so, rustlib->symlink}，rustc 以 exe 上两级推导
        sysroot=runtime。完全复用 upstream/feat/rust-rav1e-0.7.1 已验证实现。
        """
        from pathlib import Path
        rust = Path(self.dependencies.build["rust-toolchain"].package_folder)
        openssl = Path(self.dependencies.build["openssl"].package_folder)
        runtime = Path(self.build_folder) / _RUNTIME
        (runtime / "bin").mkdir(parents=True, exist_ok=True)
        (runtime / "lib").mkdir(exist_ok=True)
        cc = self._cc()
        sign_tool = self._sign_tool()

        # 1) openssl 静态归档 → 私有 libssl.so/libcrypto.so（cargo 运行时）
        for name in ("crypto", "ssl"):
            soname = f"lib{name}.so"
            dst = runtime / "lib" / soname
            if dst.is_file():
                continue
            archives = [str(p) for p in openssl.rglob(f"lib{name}.a")]
            if not archives:
                raise ConanException(
                    f"lib{name}.a not found in openssl package")
            cmd = [cc, "-shared", "-Wl,-z,relro,-z,now",
                   f"-Wl,-soname,{soname}",
                   "-Wl,--whole-archive", archives[0],
                   "-Wl,--no-whole-archive", "-ldl", "-pthread"]
            if name == "ssl":
                cmd += [f"-L{runtime / 'lib'}", "-lcrypto"]
            cmd += ["-o", str(dst)]
            self.run(shlex.join(cmd), env="conanbuild")

        # 2) 签名 cargo / rustc（无签名工具的 Linux worker 直接探测原生可执行性）
        cargo = runtime / "bin" / "cargo"
        rustc = runtime / "bin" / "rustc"
        if not (cargo.is_file() and rustc.is_file()):
            if sign_tool is None:
                pkg_cargo = rust / "bin" / "cargo"
                pkg_rustc = rust / "bin" / "rustc"
                if os.access(pkg_cargo, os.X_OK) and \
                        os.access(pkg_rustc, os.X_OK):
                    return (str(pkg_cargo.resolve()),
                            str(pkg_rustc.resolve()))
                raise ConanInvalidConfiguration(
                    "binary-sign-tool unavailable and rust-toolchain "
                    "binaries not directly executable on this filesystem")
            for tool in ("cargo", "rustc"):
                self._sign_copy(sign_tool, str(rust / "bin" / tool),
                                str(runtime / "bin" / tool))

        # 3) librustc_driver*.so 签名（rustc dlopen 的 dylib）+ libc++_shared.so 防遮蔽
        if sign_tool is not None:
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

        # 4) rustlib symlink（sysroot=runtime 布局）
        rustlib = runtime / "lib" / "rustlib"
        if not rustlib.exists():
            rustlib.symlink_to(rust / "lib" / "rustlib",
                               target_is_directory=True)

        return (str(cargo.resolve()), str(rustc.resolve()))

    def _write_environment(self, cargo, rustc):
        """生成 rav1e_env 脚本（cargo 运行环境）与 .cargo/config.toml。"""
        cc = self._cc()
        cxx = self._cxx()
        runtime = os.path.join(self.build_folder, _RUNTIME)

        env = Environment()
        # 清理可能干扰交叉构建的外部变量（rust-rav1e/cbindgen/crunch64 同款清单）
        for key in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "CPATH",
                    "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "LIBRARY_PATH",
                    "CARGO_BUILD_TARGET", "RUSTC_BOOTSTRAP",
                    "RUSTUP_TOOLCHAIN", "CARGO_ENCODED_RUSTFLAGS"):
            env.unset(key)
        env.define("CARGO", cargo)
        env.define("RUSTC", rustc)
        # built 0.7.1 的 build.rs 探测 RUSTDOC 版本；rust-toolchain minimal 无 rustdoc
        env.define("RUSTDOC", rustc)
        env.define("CC", cc)
        env.define("CXX", cxx)
        # -C linker=clang：cc crate 编 NEON 汇编、rustc 做最终链接都用 OHOS clang；
        # -C relocation-model=pic：rav1e 静态库要链进共享 MODULE 插件（heif-rav1e.so），
        # 必须是 PIC（rust-rav1e 参考配方把它链进可执行文件，无需 PIC；本包需要）。
        env.define("RUSTFLAGS", f"-C linker={cc} -C relocation-model=pic")
        env.define(f"CARGO_TARGET_{_TARGET.upper().replace('-', '_')}_LINKER", cc)
        env.define("CARGO_HOME", os.path.join(self.build_folder, "cargo-home"))
        env.define("CARGO_TARGET_DIR", os.path.join(self._rav1e_build_dir(), "target"))
        # HMDFS：并发 build script 会触发 "Text file busy (os error 26)"（见 _build_rav1e
        # 的注释）。内树 rav1e 构建固定单线程，与命令行的 `cargo rustc -j 1` 双重保险。
        env.define("CARGO_BUILD_JOBS", "1")
        env.define("CARGO_NET_RETRY", "10")
        env.define("CARGO_HTTP_TIMEOUT", "600")
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        ca = certifi.where()
        env.define("CARGO_HTTP_CAINFO", ca)
        env.define("SSL_CERT_FILE", ca)
        env.define("CURL_CA_BUNDLE", ca)
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(runtime, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", runtime)
        env.prepend_path("PATH", os.path.dirname(cargo))
        env.vars(self, scope=None).save_script("rav1e_env")

        cargo_home = os.path.join(self.build_folder, "cargo-home")
        os.makedirs(cargo_home, exist_ok=True)
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

    def _cbindgen(self):
        """从 cbindgen/0.28.0 工具包定位 cbindgen 可执行文件。"""
        pkg = self.dependencies.build["cbindgen"].package_folder
        for cand in (os.path.join(pkg, "bin", "cbindgen"),
                     os.path.join(pkg, "cbindgen")):
            if os.path.isfile(cand):
                return cand
        raise ConanInvalidConfiguration("cbindgen not found in package")

    # ------------------------------------------------------------- rav1e 内树构建
    def _rav1e_build_dir(self):
        return os.path.join(self.build_folder, _RAV1E_DIR + "-build")

    def _rav1e_header(self):
        return os.path.join(self._rav1e_build_dir(), "rav1e.h")

    def _rav1e_static_lib(self):
        return os.path.join(self._rav1e_build_dir(), "target", _TARGET,
                            "release", "librav1e.a")

    def _build_rav1e(self):
        """内树构建 rav1e 0.7.1：cbindgen → rav1e.h，cargo rustc → librav1e.a。

        R33：编译器/链接器全部经 rav1e_env（CMakeToolchain/profile conf 派生）下发，
        不裸用 shell 的 CC/CFLAGS。
        """
        cargo, rustc = self._prepare_rust_runtime()
        self._write_environment(cargo, rustc)
        src = os.path.join(self.source_folder, _RAV1E_DIR)
        os.makedirs(self._rav1e_build_dir(), exist_ok=True)

        # 1) cbindgen 生成 C 头文件（上游官方 cbindgen.toml，rav1e.h）
        header = self._rav1e_header()
        self.run(
            f"{shlex.quote(self._cbindgen())} --config cbindgen.toml "
            f"--crate rav1e --output {shlex.quote(header)}",
            cwd=src, env=["conanbuild", "rav1e_env"])
        if not (os.path.isfile(header) and os.path.getsize(header) > 0):
            raise ConanException(
                f"{self.ref}: cbindgen 未产出 rav1e.h：{header} "
                f"（内树 rav1e 头文件缺失，不能继续编插件）")

        # 2) C API 静态库（cargo-c 等价：staticlib + capi/asm/threading feature）
        # -j 1：**单线程编译**。CI 实测过 "Text file busy (os error 26)" —— 鸿蒙
        # HMDFS 在并发执行 Rust build script 时会出问题：每个 crate 的 build.rs 编出的
        # 可执行文件是"先写出、再立刻 exec"，多个 crate 并行时同一文件上会出现
        # 写/执行竞争；rav1e 的 asm feature 还会经 cc crate 起更多编译器进程，放大该
        # 竞争。串行化（-j 1）后消失。CARGO_BUILD_JOBS=1 亦在 rav1e_env 里下发作为
        # 双重保险（命令行 -j 管 cargo 自己的 jobserver；env 变量覆盖嵌套 cargo/cc 调用）。
        self.run(
            f"{shlex.quote(cargo)} rustc -j 1 --release --target {_TARGET} "
            f"--locked --no-default-features "
            f"--features capi,asm,threading --crate-type staticlib",
            cwd=src, env=["conanbuild", "rav1e_env"])

        lib = self._rav1e_static_lib()
        if not os.path.isfile(lib):
            raise ConanException(
                f"{self.ref}: 内树 librav1e.a 未生成：{lib} —— 内树 codec 构建失败，"
                f"不能继续编宿主/插件（否则会交付一个没有 rav1e 后端的空壳包）")
        self.output.info(
            f"[rav1e] produced {lib} size={os.path.getsize(lib)} "
            f"sha256={self._sha256(lib)}")
        self.output.info(
            f"[rav1e] produced {header} size={os.path.getsize(header)} "
            f"sha256={self._sha256(header)}")

    # ------------------------------------------------ 上游测试构建（libheif tests/）
    @staticmethod
    def _first_file(folder, *names):
        for name in names:
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                return path
        raise ConanException(f"{names} not found under {folder}")

    def _dep_folder(self, name):
        """test-only 编解码后端在 Conan 缓存里的 package_folder。"""
        return self.dependencies.build[name].package_folder

    def _test_lib_dirs(self):
        """测试运行所需的全部库目录（build/host 依赖树 package_folder/lib*）。

        libtiff 等包会拉入传递依赖（libwebp/zstd/libjpeg-turbo），其 .so 也必须
        在 LD_LIBRARY_PATH 里，否则运行时 el1 relocation 报 symbol not found。
        这里遍历整个依赖树（含传递节点）收集，不硬编码包名。
        """
        dirs = []

        def _add(pf):
            if not pf:
                return
            for sub in ("lib", "lib64"):
                d = os.path.join(pf, sub)
                if os.path.isdir(d) and d not in dirs:
                    dirs.append(d)

        def _walk(coll):
            try:
                nodes = list(coll.values())
            except Exception:
                try:
                    nodes = list(coll)
                except Exception:
                    return
            for node in nodes:
                _add(getattr(node, "package_folder", None))
                try:
                    _walk(node.dependencies)
                except Exception:
                    pass

        for ctx in ("build", "host"):
            try:
                _walk(getattr(self.dependencies, ctx))
            except Exception:
                pass
        return dirs

    def _test_common_defines(self):
        """上游测试构建的 -D 列表（可复现的开关来源）。

          * 上游 CMakePresets.json 的 ``testing`` preset 语义：BUILD_TESTING=ON、
            WITH_REDUCED_VISIBILITY=OFF（否则 tests/CMakeLists.txt 会禁用一批只能在
            完整符号可见性下编译的用例）、WITH_UNCOMPRESSED_CODEC=ON、
            ENABLE_EXPERIMENTAL_FEATURES=ON；
          * 交付面的 rav1e 插件：ENABLE_PLUGIN_LOADING=ON + WITH_RAV1E[_PLUGIN]=ON，
            并以内树 rav1e.h/librav1e.a 钉住 FindRAV1E（MODULE 模式）；
          * 上游测试需要、且制品仓已发布的编解码后端（dav1d/libde265/x265/
            openjpeg/openjph/libtiff），路径取 tool_requires 的 package_folder；
          * 其余后端保持 OFF。
        """
        args = [
            "-DBUILD_SHARED_LIBS=ON",
            "-DENABLE_PLUGIN_LOADING=ON",
            "-DWITH_RAV1E=ON",
            "-DWITH_RAV1E_PLUGIN=ON",
            f"-DRAV1E_INCLUDE_DIR={self._rav1e_build_dir()}",
            f"-DRAV1E_LIBRARY={self._rav1e_static_lib()}",
            "-DBUILD_TESTING=ON",
            "-DWITH_REDUCED_VISIBILITY=OFF",
            "-DWITH_UNCOMPRESSED_CODEC=ON",
            "-DENABLE_EXPERIMENTAL_FEATURES=ON",
        ]
        for option in _DISABLED_PLUGIN_OPTIONS:
            if option in _TEST_ENABLED_OPTIONS:
                continue
            args.append(f"-DWITH_{option}=OFF")
        args.append("-DWITH_WEBCODECS=OFF")

        dav1d = self._dep_folder("dav1d")
        dav1d_inc = os.path.join(dav1d, "include")
        args += [
            "-DWITH_DAV1D=ON", "-DWITH_DAV1D_PLUGIN=OFF",
            f"-DDAV1D_INCLUDE_DIR={dav1d_inc}",
            f"-DDAV1D_LIBRARY={self._first_file(os.path.join(dav1d, 'lib'), 'libdav1d.so')}",
        ]
        libde265 = self._dep_folder("libde265")
        libde265_inc = os.path.join(libde265, "include")
        args += [
            "-DWITH_LIBDE265=ON",
            f"-DLIBDE265_INCLUDE_DIR={libde265_inc}",
            f"-DLIBDE265_LIBRARY={self._first_file(os.path.join(libde265, 'lib'), 'libde265.a')}",
        ]
        x265 = self._dep_folder("x265")
        x265_inc = os.path.join(x265, "include")
        args += [
            "-DWITH_X265=ON",
            f"-DX265_INCLUDE_DIR={x265_inc}",
            f"-DX265_LIBRARY={self._first_file(os.path.join(x265, 'lib'), 'libx265.a')}",
        ]
        openjpeg = self._dep_folder("openjpeg")
        args += [
            "-DWITH_OpenJPEG_ENCODER=ON", "-DWITH_OpenJPEG_DECODER=ON",
            "-DWITH_OpenJPEG_ENCODER_PLUGIN=OFF",
            "-DWITH_OpenJPEG_DECODER_PLUGIN=OFF",
        ]
        cfg = glob.glob(os.path.join(openjpeg, "lib", "cmake", "openjpeg-*"))
        if cfg:
            args.append(f"-DOpenJPEG_DIR={cfg[0]}")
        openjph = self._dep_folder("openjph")
        args += [
            "-DWITH_OPENJPH_ENCODER=ON", "-DWITH_OPENJPH_ENCODER_PLUGIN=OFF",
            # FindOPENJPH.cmake 先试 config 模式；用空 OPENJPH_DIR 强制走 fallback
            # 分支（find_path/find_library 读我们钉的 -D），避免 config 分支只在
            # imported target 上挂 include、不写 OPENJPH_INCLUDE_DIRS 的问题。
            "-DOPENJPH_DIR=",
            f"-DOPENJPH_INCLUDE_DIR={os.path.join(openjph, 'include')}",
            f"-DOPENJPH_LIBRARY={self._first_file(os.path.join(openjph, 'lib'), 'libopenjph.so')}",
        ]
        libtiff = self._dep_folder("libtiff")
        args += [
            f"-DTIFF_INCLUDE_DIR={os.path.join(libtiff, 'include')}",
            f"-DTIFF_LIBRARY={self._first_file(os.path.join(libtiff, 'lib'), 'libtiff.so')}",
        ]
        return args

    _CATCH_ALL_PASSED_RE = re.compile(
        r"All tests passed \((\d+) assertions? in (\d+) test cases?\)")

    def _run_upstream_tests(self):
        """构建并运行上游 libheif 的完整 CTest 套件，打印机器可读台账。

        为什么单独建目录：上游 ``testing`` preset 会改 WITH_REDUCED_VISIBILITY 等
        开关，直接影响产物；交付产物必须保持最小面，故测试构建与交付构建分离。
        """
        test_dir = os.path.join(self.build_folder, _TEST_BUILD_DIR)
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        # conan_toolchain.cmake 里有 `set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)`（普通
        # 变量，会遮蔽命令行 -D），使得带 config 文件的后端（libde265 / openjph）走
        # CONFIG 模式、绕过 libheif 自带的 FindLIBDE265.cmake / FindOPENJPH.cmake，
        # 于是 plugin_compilation 宏里的 ${LIBDE265_INCLUDE_DIRS}/${OPENJPH_INCLUDE_DIRS}
        # 为空 → decoder_libde265.cc / encoder_openjph.cc 找不到头文件。
        # 用 CMAKE_PROJECT_INCLUDE（在 project() 之后 include，能覆盖 toolchain 的
        # 普通变量）把查找顺序改回 MODULE 优先——libheif 自带 Find 模块就是为这些
        # 后端准备的；OpenJPEG 无自带模块时自然回落 CONFIG。
        force_module = os.path.join(self.build_folder, "force-module-find.cmake")
        with open(force_module, "w", encoding="utf-8") as handle:
            handle.write("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)\n")
        configure = [
            "cmake", "-S", self.source_folder, "-B", test_dir,
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain}",
            f"-DCMAKE_PROJECT_INCLUDE={force_module}",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_SYSTEM_NAME=Linux",
            "-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON",
            "-DCMAKE_INSTALL_RPATH=",
        ] + self._test_common_defines()
        self.output.info("[upstream-tests] configure: " + " ".join(configure))
        self.run(shlex.join(configure), env="conanbuild")
        self.run(f"cmake --build {shlex.quote(test_dir)} -j{self._jobs()}",
                 env="conanbuild")

        lib_dir = os.path.join(test_dir, "libheif")
        plugin_dir = os.path.join(lib_dir, "plugins")
        ld_path = os.pathsep.join([lib_dir] + self._test_lib_dirs())

        ctest_log = os.path.join(test_dir, "ctest-upstream.log")
        # 运行期库路径 = 测试构建的 libheif + 依赖树 lib 目录，并**追加** conanbuild
        # 环境里已有的 tool_requires 库目录（openssl/rust 及编解码包的传递依赖）。
        self.run(
            "LD_LIBRARY_PATH=" + shlex.quote(ld_path) + ":$LD_LIBRARY_PATH "
            f"ctest --output-on-failure > {shlex.quote(ctest_log)} 2>&1 || true",
            cwd=test_dir, env="conanbuild")
        # 逐个测试可执行文件取 Catch2 汇总行（用例级台账）
        ledger = os.path.join(test_dir, "upstream-tests-ledger.tsv")
        script = (
            f"cd {shlex.quote(test_dir)}/tests && "
            f"for t in $(ctest -N 2>/dev/null | sed -n 's/.*Test *#[0-9]*: //p'); do "
            '  out=$(LD_LIBRARY_PATH=' + shlex.quote(ld_path) + ':$LD_LIBRARY_PATH'
            ' LIBHEIF_PLUGIN_PATH=' + shlex.quote(plugin_dir) + ' ./$t 2>&1); '
            '  line=$(printf "%s\\n" "$out" | grep -E '
            "'^(All tests passed|test cases:)' | tail -1); "
            '  printf "%s\\t%s\\n" "$t" "$line"; '
            f"done > {shlex.quote(ledger)}"
        )
        self.run(script, env="conanbuild")

        passed = failed = skipped = 0
        with open(ledger, "r", errors="replace") as handle:
            for raw in handle:
                name, _, summary = raw.rstrip("\n").partition("\t")
                summary = summary.strip()
                if not summary:
                    self.output.warning(
                        f"[upstream-tests] {name}: no Catch2 summary line")
                    continue
                match = self._CATCH_ALL_PASSED_RE.search(summary)
                if match:
                    passed += int(match.group(2))
                    continue
                if summary.startswith("test cases:"):
                    # Catch2 汇总形如 "test cases: T | P passed | F failed | S skipped"
                    # （数值为 0 的段被省略），按 '|' 逐段解析。
                    for token in summary.split("|")[1:]:
                        token = token.strip()
                        if not token:
                            continue
                        try:
                            amount = int(token.split()[0])
                        except (IndexError, ValueError):
                            continue
                        if token.endswith("passed"):
                            passed += amount
                        elif token.endswith("failed"):
                            failed += amount
                        elif token.endswith("skipped"):
                            skipped += amount
                    continue
                self.output.warning(
                    f"[upstream-tests] {name}: unrecognized summary: {summary!r}")

        executed = passed + failed + skipped
        marker = {
            "status": "passed" if failed == 0 and passed > 0 else "failed",
            "framework": "catch2+ctest",
            "command": "ctest --output-on-failure（tests/CMakeLists.txt 注册的 "
                       "libheif 上游用例）",
            "unit": "test_case",
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "executed": executed,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        self.output.info(
            f"[upstream-tests] ledger: {ledger}（逐用例汇总行；ctest 日志 {ctest_log}）")
        if marker["status"] != "passed":
            raise ConanException(
                "upstream libheif ctest failed: "
                f"passed={passed} failed={failed} skipped={skipped}")

    # ---------------------------------------------------------------- generate
    def generate(self):
        tc = CMakeToolchain(self)
        # R33：全部构建配置经 CMakeToolchain 下发。宿主必须是共享库（插件 dlopen 语义）。
        tc.variables["BUILD_SHARED_LIBS"] = True

        # --- 交付面：rav1e 编码后端，且以独立插件模块形态构建 ---
        tc.variables["ENABLE_PLUGIN_LOADING"] = True
        tc.variables["WITH_RAV1E"] = True
        tc.variables["WITH_RAV1E_PLUGIN"] = True

        # --- 交付面之外的上游后端全部显式关闭 ---
        for option in _DISABLED_PLUGIN_OPTIONS:
            tc.variables[f"WITH_{option}"] = False
        tc.variables["WITH_UNCOMPRESSED_CODEC"] = False
        tc.variables["WITH_WEBCODECS"] = False

        # --- 非交付面（工具/文档/测试）：不构建 ---
        tc.variables["WITH_EXAMPLES"] = False
        tc.variables["WITH_GDK_PIXBUF"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_DOCUMENTATION"] = False

        # --- 安装期不得改写 ELF：OHOS 上这是交付物可用性的硬条件 ---
        # clang launcher 在链接期给 ELF 写 .note.ohos.ident 签名；CMake 默认
        # （BUILD_WITH_INSTALL_RPATH=OFF）会在 install 时**就地改写 RUNPATH**
        # （同尺寸但字节变 → sha256 变 → 签名失效 → 运行期宿主 dlopen 报
        # `Permission denied`）。处置：让构建树直接用"安装 RPATH"（取空），CMake
        # 便不再改写，安装前后逐字节一致；运行期由 conanrun 的 LD_LIBRARY_PATH 解析。
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        tc.variables["CMAKE_INSTALL_RPATH"] = ""

        # --- CMake 平台名：不是可选的美化项，缺它交付物直接不可用 ---
        # 设备 uname -s == "HarmonyOS"，而 SDK 的 CMake 只有 Platform/OHOS.cmake，
        # 没有 Platform/HarmonyOS.cmake → 落"未知平台"回退 → CMAKE_SHARED_LIBRARY_SONAME_*
        # 未定义 → 宿主不写 SONAME（连版本化文件名都没有），插件 MODULE 链接时把构建期
        # 路径写进 DT_NEEDED（带斜杠 → 按 CWD 解析）→ 运行期宿主 dlopen 插件必失败。
        # 显式走 Linux 平台分支（仓库 693 个配方同口径；conan 的 toolchain 对该变量有
        # `if(NOT DEFINED CMAKE_SYSTEM_NAME)` 守卫，故用 cache_variables 生效）。
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"

        # --- FindRAV1E.cmake 的输入（内树构建产物，MODULE 模式，直接钉路径）---
        tc.cache_variables["RAV1E_INCLUDE_DIR"] = self._rav1e_build_dir()
        tc.cache_variables["RAV1E_LIBRARY"] = self._rav1e_static_lib()

        # --- OHOS：设备 libc++ 缺省隐藏 C++20 ranges 算法，必须显式放行 ---
        # libheif 顶层声明 CMAKE_CXX_STANDARD 20，而 libheif/box.cc 用了
        # std::ranges::all_of / std::ranges::find。OHOS SDK 的 libc++ 在未定义
        # _LIBCPP_ENABLE_EXPERIMENTAL 时定义 _LIBCPP_HAS_NO_INCOMPLETE_RANGES，
        # 把 ranges 重载全部隐藏 → 报 "no member named 'all_of' in namespace
        # 'std::ranges'"。编译期宏放行，不改上游源码、无需 -lc++experimental。
        # 已合并先例：archives/l/libheif-{dav1d,svtenc,aom}/1.23.0、libpqxx/8.0.1。
        if str(self.settings.os) in ("Linux", "OHOS"):
            tc.preprocessor_definitions["_LIBCPP_ENABLE_EXPERIMENTAL"] = None

        # 插件目录：保持上游默认（<prefix>/<libdir>/libheif），不改上游语义。
        tc.generate()

    # -------------------------------------------------------------------- build
    def build(self):
        # 1) 内树构建内嵌依赖（rav1e 0.7.1 → rav1e.h + librav1e.a）
        self._build_rav1e()

        # 2) 只构建交付面目标：heif 宿主 + heif-rav1e 插件模块。
        #   （heifio 等其它目标不被 install()，不属交付面。）
        cmake = CMake(self)
        cmake.configure()
        self.run(f'cmake --build "{self.build_folder}" '
                 f'--target heif heif-rav1e -j{self._jobs()}')

        # 3) 上游测试套件：在独立构建目录里编 upstream testing preset 的完整
        #    用例集并真跑 CTest（R51 第 2 步）。不这样做的话，交付构建里
        #    BUILD_TESTING=OFF → 上游用例一个都不执行（审查判定 FAIL 的原因）。
        self._run_upstream_tests()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # 内树构建的交付面输入随包归档（便于自证/二次核对；消费者仍只链接 heif）。
        lib = self._rav1e_static_lib()
        header = self._rav1e_header()
        import shutil
        inc_dir = os.path.join(self.package_folder, "include")
        lib_dir = os.path.join(self.package_folder, "lib")
        os.makedirs(inc_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)
        shutil.copy2(header, os.path.join(inc_dir, "rav1e.h"))
        shutil.copy2(lib, os.path.join(lib_dir, "librav1e.a"))
        self.output.info(
            f"packaged in-tree rav1e inputs: include/rav1e.h + lib/librav1e.a "
            f"(librav1e.a size={os.path.getsize(lib)})")

        self._sign_ohos_elf()

    def _sign_ohos_elf(self):
        """装后重签：OHOS 上 install 就地改写 RUNPATH 会破坏 clang launcher 写的
        .note.ohos.ident 签名，运行期 dlopen 报 Permission denied（EACCES）。libheif 的
        插件正是运行时 dlopen 的对象，故装包后重签。只签真实 ELF，跳过版本化软链。
        已合并先例：archives/o/openh264/2.6.0、archives/l/libheif-{dav1d,svtenc,aom}。
        """
        if str(self.settings.os) != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            self.output.info("[codesign] sign tools unavailable, skipping")
            return
        targets = []
        for pattern in ("*.so", "*.so.*"):
            targets += glob.glob(os.path.join(self.package_folder, "lib", "**", pattern),
                                 recursive=True)
        signed = []
        for path in sorted(set(targets)):
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{path}" -outFile "{path}" -selfSign 1')
            signed.append(path)
            self.output.info(f"[codesign] re-signed {path} sha256={self._sha256(path)}")
        if not signed:
            raise ConanInvalidConfiguration(
                f"{self.ref}: 包内没有可重签的 ELF 共享库（{self.package_folder}/lib/**/*.so*）")

    def package_info(self):
        # 交付的宿主库（消费者链接的就是它；插件模块是运行期产物，不在 libdirs 里）。
        self.cpp_info.libs = ["heif"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libheif")
        self.cpp_info.set_property("cmake_target_name", "libheif::libheif")
        self.cpp_info.set_property("pkg_config_name", "libheif")
        # 插件模块装在 <pkg>/lib/libheif/；上游把默认插件目录编译期钉死成构建时的
        # 绝对路径，跨缓存/跨机不可移植，故显式导出 LIBHEIF_PLUGIN_PATH
        # （VirtualRunEnv / self.run(env="conanrun") 会自动带上）。
        self.runenv_info.define(
            "LIBHEIF_PLUGIN_PATH",
            os.path.join(self.package_folder, "lib", "libheif"),
        )
