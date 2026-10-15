# libheif-rav1e 1.23.0 适配笔记

## 软件信息

- 上游（父 tarball）: <https://github.com/strukturag/libheif> 1.23.0
- 上游（内树构建的编码器）: <https://github.com/xiph/rav1e> 0.7.1
- 交付面: 上游 libheif 树内 CMake MODULE 目标 `heif-rav1e` → `lib/libheif/libheif-rav1e.so`
- 语言: C++（父 tarball 插件适配源 `libheif/plugins/encoder_rav1e.cc`）+ Rust（内树 rav1e）
- 构建系统: CMake（父 tarball）+ cargo（内树 rav1e，OHOS Rust 工具链）
- 编译环境: HarmonyOS PC（aarch64, HongMeng Kernel 1.12.0），clang 15.0.4（`/data/service/hnp/bin/clang`），conan 2.29.1（OHOS 适配版），Python 3.14.6
- 编译日期: 2026-09-27

## 一、背景与选型核实

libheif 把「编解码后端」做成可独立装载的 MODULE 插件：树内目标 `heif-<name>` →
`libheif-<name>.so`，安装到 `<libdir>/libheif/`，由宿主 `heif_init()` 运行时 `dlopen` 并注册。
本包交付其中 **rav1e（AV1 编码）** 那一个，是 libheif 一族子包中的编码侧成员
（同批已归档：`libheif-libde265`/`-openh264`/`-openjpeg`/`-svtenc`/`-aom`/`-dav1d`）。

上游开关（`libheif/plugins/CMakeLists.txt`）：

```
plugin_option(RAV1E "Rav1e AV1 encoder" OFF ON)
  →  WITH_RAV1E 默认 OFF、WITH_RAV1E_PLUGIN 默认 ON
set(RAV1E_sources encoder_rav1e.cc encoder_rav1e.h)
set(RAV1E_extra_plugin_sources ../error.cc)
plugin_compilation(rav1e RAV1E RAV1E_FOUND RAV1E RAV1E)
  →  ENABLE_PLUGIN_LOADING=ON + WITH_RAV1E=ON + WITH_RAV1E_PLUGIN=ON 时
     add_library(heif-rav1e MODULE ...) → libheif-rav1e.so
```

三维核验：

- 制品仓：`rav1e`/`librav1e`/`rust-rav1e` 任何版本都不存在（W0 实测，下节）；
- 平台归档：`archives/l/` 下无 `libheif-rav1e` 任何历史（骨架/归档均无）；
- 上游：libheif v1.23.0 与 rav1e v0.7.1 GitHub tag 归档实存。

语言预检（R47）：`lang-preflight libheif-rav1e 1.23.0 --src <libheif src>` → `detected=cpp`
（manifest=CMakeLists.txt `project(libheif LANGUAGES C CXX VERSION 1.23.0)`，构建系统=cmake，
源文件 229 个、主体 cpp 占比 95%），与任务语言 `cpp` 一致，通过。

## 二、W0 依赖判定（适配第一件事，先查依赖再动手）

### 2.1 rav1e 未发布（三条 ref 均为空）

```
$ conan download "rav1e/*" -r=ohpcd --only-recipe
Connecting to remote 'ohpcd' anonymously
Found 0 pkg/version recipes matching rav1e/* in ohpcd
WARN: No packages were downloaded because the package list is empty.

$ conan download "librav1e/*" -r=ohpcd --only-recipe
Found 0 pkg/version recipes matching librav1e/* in ohpcd

$ conan download "rust-rav1e/*" -r=ohpcd --only-recipe
Found 0 pkg/version recipes matching rust-rav1e/* in ohpcd
```

判据按 **R35**：只看 `Found N ... recipes` 行（0），**不看** exit code / `conan list` 回显 /
`Local Cache` 段（cnb.cool 搜索 API 对 binary 返回不完整）。

### 2.2 Rust 工具链**已发布**（tool_requires 可用）

```
$ conan download "rust-toolchain/1.97.1" -r=ohpcd --only-recipe
  rust-toolchain/1.97.1
    revisions
      874ec05d07ae08465bb25281d1d9a543 (2026-09-09 13:10:23 UTC)     # 命中

$ conan download "cbindgen/0.28.0" -r=ohpcd --only-recipe
  cbindgen/0.28.0
    revisions
      b04343680b93ade1a6a41f5d8c11b194 (2026-09-10 15:36:30 UTC)     # 命中

$ conan download "openssl/3.5.6.1.1" -r=ohpcd --only-recipe
  openssl/3.5.6.1.1
    revisions
      b83d5ca745c3e2265a9ba67e4d3546a6 (2026-08-04 12:11:17 UTC)     # 命中
```

三者的 **binary** 亦可用（`conan install --build=missing` 实测：从 ohpcd 直接
`Package installed`，无需源码构建）。CI 能力矩阵里 Rust 一行写着「❌ 无系统级 rustc / cargo →
Rust 包直接 env_unsupported（除非先立项 rust 工具链包）」——**本任务正属该例外**：
`rust-toolchain/1.97.1` 已作为包发布，故以 `tool_requires` 补齐，`cargo`/`rustc` 由该包提供。

crates.io 镜像可达性（rav1e 的依赖闭包需下载 crates）：

```
$ curl -sS -o /dev/null -w "%{http_code}" https://rsproxy.cn/index/config.json
200
```

### 2.3 结论与决策（R36 + 仓库先例）

- **不**声明 `self.requires("rust-rav1e/0.7.1")`（或任何 rav1e ref）：它没发布 → R36 机械门禁
  （`finish` step[5/10] / CI L0i / preflight PF4 逐条 `conan download --only-recipe`）必然 Hard-Fail。
- 采用仓库对「未发布编码器依赖」的既有先例——**包内树构建**：`libheif-svtenc`（内树 SVT-AV1）、
  `libheif-aom`（内树 libaom）、`handbrake/1.11.2`（contribs 内树、无 Conan 依赖）。
  以 `tool_requires("rust-toolchain/1.97.1") + cbindgen/0.28.0 + openssl/3.5.6.1.1` 在包内树
  构建官方 rav1e 0.7.1 → `librav1e.a` + `rav1e.h`，再编 `heif-rav1e` 插件。
  结果 = 零 Conan `requires` → R36 干净、自包含、CI 可复现。
- rav1e 的构建方式完全复用仓库 upstream 分支上已验证的权威配方
  （`git show upstream/feat/rust-rav1e-0.7.1:archives/r/rust-rav1e/0.7.1/conanfile.py`）：
  自签 cargo/rustc/librustc_driver 私有拷贝；openssl 静态归档 `--whole-archive` relink
  私有 libssl/libcrypto；`RUSTDOC=rustc`（built 0.7.1 探测）；rsproxy.cn sparse 镜像。

### 2.4 网络与源码获取（真实读数）

- libheif v1.23.0 tarball sha256 = `50ea4fbd1e19c7b8820271d6d0c73f2623fec5d659ce9fae57e48dbeb94fab9a`
  （设备实测下载后 `sha256sum`，与同批 6 个 libheif 子包逐字节一致）。
- rav1e v0.7.1 tarball sha256 = `da7ae0df2b608e539de5d443c096e109442cdfa6c5e9b4014361211cf61d030c`
  （设备实测下载后 `sha256sum`，与 upstream 分支 rust-rav1e/0.7.1 conandata.yml 声明值一致）。
- 适配期实测 `github.com` 时通时断（`curl https://github.com` 曾 HTTP 000 timeout，而
  `codeload.github.com` 稳定 HTTP 200/301）；libheif/rav1e 的官方归档端点 `github.com/.../archive/...`
  实为重定向到 `codeload.github.com`，两者字节一致（故 sha256 相同）。为让本地 `conan create`
  不受该抖动影响，把两个官方 tarball 预置进 conan 本地下载缓存
  （`core.sources:download_cache`，默认 `~/.conan2/downloads/s/<sha256>`），`get()` 即从缓存取用。
  conandata.yml 仍声明**官方源 URL**（R39）；CI 侧有独立的预下载 + 镜像回退
  （`ci/conan/build_and_test.sh` 只扫 conandata.yml 的 URL）。

## 三、交付形态（自包含）

| 产物 | 生成方式 | 说明 |
|------|---------|------|
| `lib/libheif/libheif-rav1e.so`（+ VERSION/SOVERSION 软链） | 上游树内 `encoder_rav1e.cc` 编成 MODULE，静态链入 `librav1e.a` | **本包命名产物**（AV1 编码插件） |
| `lib/libheif.so` / `libheif.so.1` | 同源同版本、`ENABLE_PLUGIN_LOADING=ON` 的宿主 | 插件运行期由它 `dlopen`，不能来自 codec-free 的 `libheif/1.22.2` |
| `lib/librav1e.a` + `include/rav1e.h` | 包内树构建 rav1e 0.7.1（官方源） | 交付面输入（随包归档便于自证；消费者默认只链接 `heif`） |
| `include/libheif/*.h`、`lib/pkgconfig/libheif.pc`、`lib/cmake/libheif/*` | 父 tarball install | 消费者链接/查找信息 |

## 四、编译步骤

1. `source()`：`get()` 父 tarball（libheif 1.23.0，strip_root）+ `get()` rav1e 0.7.1 到
   `source_folder/rav1e`；`apply_conandata_patches()`（`patches: {}` → no-op）。
2. `build()` 第 1 步 `_build_rav1e()`：
   - `_prepare_rust_runtime()`：openssl 静态归档 relink 私有 `libssl.so`/`libcrypto.so`；
     `binary-sign-tool` 自签 cargo/rustc/librustc_driver 私有拷贝；`rustlib` 软链；
   - `_write_environment()`：生成 `rav1e_env` 脚本（`CC`/`CXX`/`RUSTFLAGS=-C linker=clang
     -C relocation-model=pic`/`RUSTDOC=rustc`/`CARGO_*`）+ `.cargo/config.toml`（rsproxy.cn sparse）；
   - `cbindgen --config cbindgen.toml --crate rav1e --output <build>/rav1e-build/rav1e.h`；
   - `cargo rustc --release --target aarch64-unknown-linux-ohos --locked --no-default-features
     --features capi,asm,threading --crate-type staticlib` → `librav1e.a`。
3. `build()` 第 2 步：`cmake configure` + `cmake --build ... --target heif heif-rav1e -j4`。
4. `package()`：`cmake install`；把 `rav1e.h` / `librav1e.a` 归档进包；OHOS 上装后重签所有
   真实 ELF `.so`（`llvm-objcopy --remove-section .codesign` + `binary-sign-tool -selfSign 1`）。
5. `test_package`：`conan create` 自动编译并运行消费者测试（宿主 dlopen 插件 + 真实 AV1 编码），
   并真跑上游 rav1e `cargo test`（R51）。

### CMake 关键开关

```
-DBUILD_SHARED_LIBS=ON
-DENABLE_PLUGIN_LOADING=ON           # 交付面：以独立插件模块构建
-DWITH_RAV1E=ON                      # 交付面：rav1e 编码后端
-DWITH_RAV1E_PLUGIN=ON               # 交付面：MODULE 形态（→ libheif-rav1e.so）
-DWITH_LIBDE265=OFF -DWITH_X265=OFF -DWITH_X264=OFF -DWITH_AOM_DECODER=OFF
-DWITH_AOM_ENCODER=OFF -DWITH_DAV1D=OFF -DWITH_KVAZAAR=OFF -DWITH_UVG266=OFF
-DWITH_VVDEC=OFF -DWITH_VVENC=OFF -DWITH_FFMPEG_DECODER=OFF -DWITH_OpenH264_DECODER=OFF
-DWITH_SvtEnc=OFF -DWITH_JPEG_DECODER=OFF -DWITH_JPEG_ENCODER=OFF
-DWITH_OpenJPEG_DECODER=OFF -DWITH_OpenJPEG_ENCODER=OFF -DWITH_OPENJPH_ENCODER=OFF
-DWITH_LIBSHARPYUV=OFF -DWITH_UNCOMPRESSED_CODEC=OFF -DWITH_WEBCODECS=OFF
-DWITH_EXAMPLES=OFF -DWITH_GDK_PIXBUF=OFF -DBUILD_TESTING=OFF -DBUILD_DOCUMENTATION=OFF
-DCMAKE_SYSTEM_NAME=Linux            # 见下（SONAME/DT_NEEDED 修复）
-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON -DCMAKE_INSTALL_RPATH=
-DRAV1E_INCLUDE_DIR=<build>/rav1e-build -DRAV1E_LIBRARY=<build>/rav1e-build/target/aarch64-unknown-linux-ohos/release/librav1e.a
```

## 五、遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|---------|
| 1 | GitHub 归档端点时通时断（`github.com` HTTP 000，`codeload.github.com` 200） | 网络抖动/限流；conan `get()` 默认对 URL 无超时，首个 URL 挂住会卡死 | 官方 tarball 预置进 conan 下载缓存（`~/.conan2/downloads/s/<sha256>`），`get()` 命中缓存不再走网；conandata 仍声明官方 URL |
| 2 | 设备 `uname -s` 报 HarmonyOS，SDK 的 CMake 无 `Platform/HarmonyOS.cmake` | 落「未知平台」回退 → `CMAKE_SHARED_LIBRARY_SONAME_*` 未定义 → 宿主不带 SONAME，插件 MODULE 把**构建期相对路径**写进 `DT_NEEDED`（含斜杠 → 按 CWD 解析）→ 运行期 dlopen 必失败 | `tc.cache_variables["CMAKE_SYSTEM_NAME"]="Linux"`（走 `Platform/Linux.cmake`；conan toolchain 有 `if(NOT DEFINED CMAKE_SYSTEM_NAME)` 守卫，故 -D 生效），宿主得到 SONAME `libheif.so.1`，插件 `DT_NEEDED` 变无斜杠可解析 |
| 3 | 设备 libc++（15.0.4）未定义 `_LIBCPP_ENABLE_EXPERIMENTAL` 时隐藏 `std::ranges::all_of/find` | 上游 libheif 声明 `CMAKE_CXX_STANDARD 20` 且 `box.cc` 用了这两个算法 → 编译期硬失败 | `generate()` 里 `tc.preprocessor_definitions["_LIBCPP_ENABLE_EXPERIMENTAL"]=None`（编译期宏，无需 `-lc++experimental`，不改上游源码） |
| 4 | cmake install 就地改写 RUNPATH 破坏 clang launcher 写的 `.note.ohos.ident` 签名 → dlopen EACCES | CMake 默认 `BUILD_WITH_INSTALL_RPATH=OFF`，install 时把构建树 RPATH 改写成安装 RPATH（同尺寸但字节变） | `-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON -DCMAKE_INSTALL_RPATH=`（构建期直接用空的安装 RPATH，install 不再改写，前后逐字节一致）；package() 末尾再对包内 ELF 重签兜底 |
| 5 | rav1e 的 `build.rs` panic（built 0.7.1 探测 RUSTDOC 版本；minimal 工具链无 rustdoc） | `rust-toolchain` 为 minimal profile，`RUSTDOC -V` spawn 报 ENOENT | 环境注入 `RUSTDOC=<签名 rustc>`（`rustc -V` 与 `rustdoc -V` 输出格式相同） |
| 6 | Rust 静态库要链进**共享** MODULE 插件 | rust-rav1e 参考配方把它链进可执行文件（无需 PIC），本包需要 PIC | `RUSTFLAGS += -C relocation-model=pic` |
| 7 | 插件（C++，MODULE）链接 `librav1e.a` 后，Rust std 的 pthread/dl/m 符号从哪来 | OHOS sysroot 的 `libpthread.a`/`libdl.a`/`libm.a` 都是 8 字节**空 stub**，符号在 `libc.so`（musl 合并）里 | 无需额外 `-l`：`clang++` 默认链 `libc.so`，实测其导出 `pthread_create`/`dlopen`/`pow`/`sqrt`/`fmod`（`llvm-nm -D --defined-only libc.so` 命中），插件链接零 undefined |
| 8 | 上游测试构建里 `decoder_libde265.cc`/`encoder_openjph.cc` 报找不到 `<libde265/de265.h>`/`<openjph/ojph_mem.h>`（其余后端正常） | `conan_toolchain.cmake` 里 `set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)`（**普通变量，遮蔽命令行 -D**）：libde265/openjph 的 Conan 包自带 `*-config.cmake`，于是 `find_package` 走 CONFIG、绕过 libheif 自带的 `FindLIBDE265.cmake`/`FindOPENJPH.cmake`，`plugin_compilation` 读的 `${LIBDE265_INCLUDE_DIRS}`/`${OPENJPH_INCLUDE_DIRS}` 就没人填 | 测试构建用 `-DCMAKE_PROJECT_INCLUDE=<写出的 cmake 文件>`（在 `project()` 之后 include，能覆盖 toolchain 的普通变量）执行 `set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)`，回到 MODULE 优先 |
| 9 | 测试台账少记 10 个用例（只统计到 29/38 个可执行文件） | `ctest -N` 打印 `Test  #1:`（两位空格）与 `Test #10:`（一位空格），台账脚本的 `sed` 只匹配了后者 | `sed -n 's/.*Test *#[0-9]*: //p'`（`Test` 后允许任意空格） |
| 10 | CI 构建报 `Text file busy (os error 26)` | 鸿蒙 **HMDFS** 并发执行 Rust build script：每个 crate 的 `build.rs` 产物是"先写出、再立刻 exec"，多 crate 并行时同一文件上出现写/执行竞争；rav1e 的 `asm` feature 还会经 `cc` crate 再起编译器进程，放大竞争 | 内树 rav1e 构建**串行化**：`cargo rustc -j 1`（`_build_rav1e()`）+ `CARGO_BUILD_JOBS=1`（`rav1e_env`）双重保险；`test_package` 的 `cargo test` 编同一批 crate，同口径加 `-j 1` + `CARGO_BUILD_JOBS=1` |

## 六、上游测试清点与运行（R51 三步法）

### 6.1 上游测试清点（静态统计）

**A. 父 tarball（libheif 1.23.0，sha256 `50ea4fbd…fab9a`）全量注册面**——本包交付面是上游
树内的 rav1e 编码后端插件（CMake 目标 `heif-rav1e`），上游 `tests/` 下的测试目标不被
`install()`、不属交付面：

| 口径 | 数量 | 取数命令 |
|------|------|---------|
| Catch2 `TEST_CASE` 注册数（用例/注册类最大值 = 主 N） | 217 | `grep -rho 'TEST_CASE' tests/*.cc \| wc -l` |
| CTest `add_test` 注册数（全开关上限） | 39 | `tests/CMakeLists.txt` 的 `add_libheif_test()` 38 + `add_heifio_test()` 1 |
| 测试源文件（`.cc`） | 41 | 含 `main.cc`/`test_utils.cc` 两个无用例文件 |
| 断言 `REQUIRE(`/`CHECK(`/`_FALSE` | 4016 | 另一单位，只披露、不并入 N |

**B. 内树构建的 rav1e 0.7.1**（cargo workspace，`cargo test`）：

| 测试类型 | 宏清点 | 来源 |
|----------|--------|------|
| `#[test]` 单元测试 | 104 | rav1e `src/**` 内嵌（api/test.rs 25、tiler.rs 11、asm/** 20、util/** 16…） |
| ivf crate 单元测试 | 3 | `ivf/src/lib.rs` |
| CLI 集成测试 | 10 | `tests/binary.rs`（assert_cmd 实跑二进制编码） |
| API doctests | 3 | `tests/doctests.rs` |
| 合计（宏清点） | 120 | quickcheck 属性测试在运行期再展开 |

### 6.2 实际运行（真机 HarmonyOS aarch64，BUILD_TESTING=ON）

> **2026-09-28 修订**：此前版本按 `BUILD_TESTING=OFF` 构建、217 项全部 NOT_RUN，PR 审查判定
> FAIL（规则要求上游测试必须真实执行）。本版改成**真跑上游 CTest 套件**。

做法（见 `conanfile.py` 的 `_run_upstream_tests()` / `_test_common_defines()`）：

| 关键点 | 内容 | 依据 |
|--------|------|------|
| 测试开关 | 上游 `CMakePresets.json` 的 **`testing` preset** 语义：`BUILD_TESTING=ON` + `WITH_REDUCED_VISIBILITY=OFF` + `WITH_UNCOMPRESSED_CODEC=ON` + `ENABLE_EXPERIMENTAL_FEATURES=ON` | 上游自带的测试配置就是这套：`REDUCED_VISIBILITY=OFF` 才会编译 `bitstream_tests`/`jpeg2000`/`mini_box` 等只能用内部符号的用例；`UNCOMPRESSED_CODEC=ON` 才会编译 `uncompressed_*` 一批 |
| 独立构建目录 | `<build>/upstream-tests`，与交付构建分开 | testing preset 会改 `WITH_REDUCED_VISIBILITY` 等开关、直接影响产物；**交付产物的开关保持最小面不变**（交付构建仍 `REDUCED_VISIBILITY` 默认 ON、`UNCOMPRESSED_CODEC=OFF`、`BUILD_TESTING=OFF`） |
| 测试所需后端 | `dav1d/1.5.0`(AV1 解码) + `libde265/1.0.18`(HEVC 解码) + `x265/4.2`(HEVC 编码) + `openjpeg/2.5.4`(J2K) + `openjph/0.31.0`(HT-J2K) + `libtiff/4.7.2.1`(heifio TIFF)，均为 ohpcd 已发布包，以 **`tool_requires`** 声明 | 上游测试的 `get_encoder_or_decoder_or_skip()` 在后端缺席时会 **Catch2 SKIP**；只跑"不 SKIP 的"不叫真实执行。用 `tool_requires` 而非 `requires`：**交付包 `requires()` 仍为空**（消费者只链 heif），这些后端只出现在 build 上下文 |
| 查找模式 | 用 `CMAKE_PROJECT_INCLUDE` 覆盖 conan toolchain 的 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`，回到 MODULE 优先 | 否则带 config 文件的 `libde265`/`openjph` 会绕过 libheif 自带的 `FindLIBDE265.cmake`/`FindOPENJPH.cmake`，`plugin_compilation` 里的 `${LIBDE265_INCLUDE_DIRS}`/`${OPENJPH_INCLUDE_DIRS}` 为空 → 找不到头文件 |
| 台账 | 跑 `ctest --output-on-failure`，再逐可执行文件解析 Catch2 汇总行，打印 `HMBS_UPSTREAM_TEST_RESULT`（用例级 PASS/FAIL/SKIP） | 与 rav1e `cargo test` 的 HMBS 标记同口径 |

**实测结果（TOTAL = PASS + FAIL + SKIP + NOT_RUN = 217，单位 = Catch2 用例）**：

| 项 | 数量 |
|----|------|
| **PASS** | **212** |
| FAIL | 0 |
| SKIP | 0 |
| NOT_RUN | 5 |
| 实际运行 **N′** | **212** |

NOT_RUN 逐项（都有具体技术原因，不是"没环境"）：

| 用例 | 数量 | 原因 |
|------|------|------|
| `encode.cc` 的 `Create images` / `Encode HDR` | 2 | **上游源码 `#if 0` 硬禁用**（`tests/encode.cc:86-104`），任何配置都跑不了 |
| `tiffdecode` 的 1 项 | 1 | 该文件顶层 `#if` 守卫（GeoTIFF 相关），本次未启用 |
| `uncompressed_decode_generic_compression` | 2 | 需要 zlib（`ZLIB_FOUND`）：libtiff 的传递依赖里有 `zlib/1.3.1.1`，但只提供静态 `libz.a`，尚未接入 `FindZLIB` |

> `ctest` 注册 **38 个可执行测试**（上游 `tests/CMakeLists.txt` 的 39 个 `add_test` 中，
> `uncompressed_decode_generic_compression` 因缺 zlib 未编译）。另：内树 rav1e 的 `cargo test`
> 在 `test_package` 阶段真跑 **452/452**（见 8.3）。

## 七、依赖说明

- **运行时零 Conan `requires`**（rav1e 静态链入插件，自包含）。
- **编译工具依赖（`tool_requires`，均已验证发布制品仓）**：
  - `rust-toolchain/1.97.1`：cargo/rustc + `aarch64-unknown-linux-ohos` std；
  - `cbindgen/0.28.0`：生成 `rav1e.h`（上游官方 `cbindgen.toml`）；
  - `openssl/3.5.6.1.1`：cargo 运行期 `libssl`/`libcrypto` relink 源（系统 libssl 3.0 缺 cargo 1.97
    所需 3.5 符号）。
- **上游测试专用编解码后端（`tool_requires`，仅为 `build()` 里的上游测试构建服务，
  不进入交付包的 `requires` 依赖面、不改变交付产物的链接面）**：
  `dav1d/1.5.0`、`libde265/1.0.18`、`x265/4.2`、`openjpeg/2.5.4`、`openjph/0.31.0`、`libtiff/4.7.2.1`。
  理由见 6.2——没有它们，上游测试里的 `get_encoder_or_decoder_or_skip()` 会整片 SKIP。

## 八、验证结果（实测读数）

构建命令：

```
$ conan create archives/l/libheif-rav1e/1.23.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --user=ohpcd --channel=stable -c tools.build:jobs=4
```

### 8.1 内树 rav1e 构建产物 + 宿主/插件（实测）

```
libheif-rav1e/1.23.0@ohpcd/stable: [rav1e] produced
  <build>/rav1e-build/target/aarch64-unknown-linux-ohos/release/librav1e.a
  size=76268686 sha256=b7bedbfa033f2b7655b41417d2904114deb1881ea5b4931b41b6ab31a85ca02a
libheif-rav1e/1.23.0@ohpcd/stable: [rav1e] produced
  <build>/rav1e-build/rav1e.h
  size=47349 sha256=9e2b7ea4f1026023819f7be17901070a39e83010240fc447b27b261f1186ef04
libheif-rav1e/1.23.0@ohpcd/stable: RUN: cmake -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE="generators/conan_toolchain.cmake"
  -DCMAKE_INSTALL_PREFIX="<cache>/p" -DCMAKE_SYSTEM_NAME="Linux"
  -DRAV1E_INCLUDE_DIR="<build>/rav1e-build"
  -DRAV1E_LIBRARY="<build>/rav1e-build/target/aarch64-unknown-linux-ohos/release/librav1e.a"
  -DCMAKE_BUILD_TYPE="Release" "<build>"
libheif-rav1e/1.23.0@ohpcd/stable: RUN: cmake --build "<build>" --target heif heif-rav1e -j4
libheif-rav1e/1.23.0@ohpcd/stable: [100%] Linking CXX shared module libheif-rav1e.so
-- Installing: <pkg>/lib/libheif/libheif-rav1e.so
libheif-rav1e/1.23.0@ohpcd/stable: package(): Packaged 2 '.so' files: libheif.so, libheif-rav1e.so
libheif-rav1e/1.23.0@ohpcd/stable: [codesign] re-signed <pkg>/lib/libheif/libheif-rav1e.so
libheif-rav1e/1.23.0@ohpcd/stable: Package '01d92cf349a0dd98ff915f4bd99a04430171517f' created
```

> 说明：`rav1e.h` 逐字节可复现（sha256 稳定）；`librav1e.a` 的 sha256 **随构建目录变化**
> （Rust 静态库内嵌含绝对路径的 debuginfo —— 同源同 flag 在两次不同 `<build>` 路径下实测
> 得到 `e367886a…` 与 `b7bedbfa…` 两个值，size 相差数十字节），属预期行为；其内容等价性由
> 插件链接成功 + 运行期 rav1e 编码成功证明（见 8.2）。

### 8.2 消费者测试（test_package，R34）：15/15 通过

```
  delivered plugin: <pkg>/lib/libheif/libheif-rav1e.so
  have_encoder(AV1)=1 have_decoder(AV1)=0 have_encoder(HEVC)=0
  heif_encoder_get_name() = Rav1e encoder v0.7.1
  [ok]   heif_context_encode_image(AV1) through the rav1e plugin succeeds
  [ok]   encoded AVIF bitstream written to disk is non-empty
RESULT: 15/15 checks passed
```

### 8.3 上游 rav1e cargo test（R51）：452/452 通过

| target | 结果 |
|--------|------|
| ivf unittests | 3 passed / 0 failed |
| rav1e lib unittests | 436 passed / 0 failed |
| rav1e bin unittests | 0 tests |
| tests/binary.rs（CLI 集成） | 10 passed / 0 failed |
| tests/doctests.rs | 3 passed / 0 failed |
| **合计** | **452 passed / 0 failed / 0 ignored（100%）** |

```
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "cargo-test",
  "discovered": 452, "executed": 452, "passed": 452, "failed": 0, "skipped": 0}
```

### 8.4 libheif 侧上游用例（CTest + Catch2，真跑）

```
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "catch2+ctest",
  "unit": "test_case", "passed": 212, "failed": 0, "skipped": 0, "executed": 212}
```

TOTAL = PASS 212 + FAIL 0 + SKIP 0 + NOT_RUN 5 = 217；逐项归因见 6.2。交付面本身的正确性另由
`test_package` 消费者验证承担（15/15，宿主 dlopen 插件并进入 rav1e 编码器）。

## 参考

- 先例配方（同类编码后端插件）：`archives/l/libheif-svtenc/1.23.0`（内树 SVT-AV1，动态）
- 先例配方（内树静态编解码器）：`archives/l/libheif-aom/1.23.0`（内树 libaom 静态）
- 先例配方（插件 MODULE + SONAME + runenv）：`archives/l/libheif-dav1d/1.23.0`
- 权威 Rust 构建手法：upstream 分支 `archives/r/rust-rav1e/0.7.1`
- 知识条目：E092（CMAKE_SYSTEM_NAME HarmonyOS 平台探测）、E207/E274（SONAME 缺失/软链）、
  E191（libc++）、E180（Rust 工具链支持 OHOS）、E345（可装载模块的私有宿主验证）、
  E524（R49 依赖注入私有 prefix）
---

**编译结束**: 2026-09-28 12:10
**最终状态**: built
