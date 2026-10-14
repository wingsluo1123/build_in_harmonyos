# jc303 0.12.3 OHOS 适配笔记（Builder）

## 构建语义

- 上游：midilab/jc303 tag v0.12.3（commit abac3b353a8eb505a45cbc884112da9e8b9b5888）。
  归档 39,118,248 字节，SHA256=1ad2e4c769f23872320a6b3f213d17ad6ea76e7b03bb65fa7d7e81761fd129ed。
- CMake≥3.15（clap-juce-extensions 子工程要求 ≥3.21；设备 cmake 4.1.2 ✓），
  project(JC303 VERSION 0.12.3)，插件目标 C++17（guitarml 子目录强制 C++20）。
- 插件格式：`juce_add_plugin(FORMATS AU VST3 LV2)` + CLAP
  （clap_juce_extensions_plugin）；AU 仅 macOS 分支自动关闭 → 实际产物
  VST3 + LV2 + CLAP。未请求 Standalone（无主程序，无 --version/--help CLI，
  L2 冒烟为 skip 属预期）。
- 上游已置 `JUCE_WEB_BROWSER=0`、`JUCE_USE_CURL=0`（根 CMakeLists），无
  webkit/curl 依赖面。

## 依赖闭包去网络化（本 run 核心工作）

上游根 CMakeLists 与 guitarml CMakeLists 全部经 FetchContent 从 GitHub 构建
期拉取，CI 无构建期网络。方案（用户已批）：

1. **JUCE → conan 包**：根 CMakeLists 的 `FetchContent_Declare(juce …)` 块
   替换为 `find_package(JUCE REQUIRED CONFIG)`（juce/8.0.5 ohpcd 已发布，
   rrev 2fdfcee76e9c350e6d329223a07f9f97，OHOS armv8/clang15/libc++/cppstd17
   包 991ac77b…）。消费范式与 juce run test_package 一致：包前缀经工具链
   变量 JUCE_PACKAGE_DIR 注入 CMAKE_PREFIX_PATH；包内官方 JUCEConfig 预置
   juceaide/juce_lv2_helper/juce_vst3_helper IMPORTED 工具与 23 个 INTERFACE
   模块。注意包内补丁只覆盖 JUCEModuleSupport.cmake 的模块分支，消费侧
   JUCEUtils.cmake 的 VST3 bundle 布局等分支仍直判
   `CMAKE_SYSTEM_NAME=="Linux"`——因此消费方工具链仍强制
   CMAKE_SYSTEM_NAME=Linux（E092；不强制则 VST3 退化为单文件 .vst3 且
   POST_BUILD moduleinfo 失配，实测 round-15 前故障）。
2. **五小件 → FETCHCONTENT_SOURCE_DIR_***（E292 先例）：
   - clap-juce-extensions@a3227c52fa082d2df33f4377ed1e050dd8a52595
   - chowdsp_utils@ffc70ba399f9afaeefb996eb14e55a1d487270b8
   - RTNeural@04cb333bc4b174760958a77c7ce076eae38fe8e4
   - math_approx@0c68d4d17242d707ba07fa7f1901692b7ed72d58
   - ea_variant（eyalamirmusic/Variant）@3fce49cfca50ba3b05026d41ffc4911a8e653378
   各源由 conandata.yml `fetchcontent` 段固定 URL+SHA256，source() 解包到
   `<source>/deps/`，generate() 经工具链变量注入。锁定 commit 与上游
   CMakeLists 声明逐一对应，未改任何依赖版本。
3. **xsimd 二跳 submodule**：RTNeural 的 modules/xsimd 为 gitlink
   a00c81f7b9e808a42aedcf7da2fbb1f9a636da34（.gitmodules →
   xtensor-stack/xsimd），RTNEURAL_XSIMD=ON 必须（STL backend 不匹配上游
   用法，不得用仓内 rtneural/1.0.0 配方）；解包到 deps/RTNeural/modules/xsimd。
   RTNeural 归档内 modules/Eigen 与 modules/json 为普通 vendored 目录已自带。
4. math_approx 经 FetchContent 注入后 PROJECT_IS_TOP_LEVEL=OFF：不触发其
   CPM 拉 xsimd master、不加测试；`if(TARGET xsimd)` 为假（RTNeural 仅 include
   xsimd 头不定义 target）→ 纯头文件路径，无额外依赖。

## OHOS 运行期闭包（E505）

- 插件 .so 的 NEEDED：freetype/fontconfig(+libxml2)/alsa 共享库 + 系统库
  （libc/libc++_shared）。X11 为 NOLINK 头依赖（juce 包内
  linuxPackages: NOLINK x11 xproto；xorgproto 真实 .pc 目录并入
  PKG_CONFIG_PATH），不产生 DT_NEEDED。
- generate()：CMAKE_MODULE_LINKER_FLAGS 与 CMAKE_SHARED_LINKER_FLAGS 双
  变量同值注入（插件格式目标是 MODULE 库，SHARED 变量对其不生效，双变量
  防格式差异）`-Wl,--disable-new-dtags -Wl,-rpath,$ORIGIN/jc303-runtime:
  $ORIGIN/../jc303-runtime:$ORIGIN/../../jc303-runtime:$ORIGIN/../../../
  jc303-runtime:$ORIGIN/../../../../jc303-runtime` —— $ORIGIN 链 5 条目
  （0/1/2/3/4 级上行），覆盖 CLAP（平级）/LV2（一级）/VST3
  （Contents/<arch> 三级，需 4 级上行至 lib 同级）各 bundle 深度；链外再
  追加包内视图（<pkg>/lib/jc303-runtime）与构建树视图两个绝对路径 rpath
  条目作双保险（juceaide 先例同款，兜底 link 环节裸 shell 剥离 $ORIGIN
  的情况）。
- package()：四依赖包全部 .so 实体化（真实文件，逐别名名一份）进
  lib/jc303-runtime/ 并逐文件 binary-sign-tool selfSign；插件 ELF 一并签名；
  最后 llvm-readelf 断言每个插件 ELF 的 NEEDED ⊆ 视图 ∪ 系统库、且
  $ORIGIN rpath 真实进入 ELF（防 shell/make 层展开失效的静默故障）。
- 测试运行时 unset LD_LIBRARY_PATH（避免压过 rpath）。

## LTO

去除 juce::juce_recommended_lto_flags（根 CMakeLists 1 处 + guitarml 2 处）：
全量 `-flto` 对三格式插件目标在 OHOS clang-15/lld 上未验证且按格式倍增链接
成本；config/warning flags 保留。记入 C_SIGNALS。

## 功能边界披露（OGG 解码裁剪）

- 已发布 juce/8.0.5 包的 oggvorbis vendored 树不完整（juce 包缺陷，已报
  juce run 修复）：`oggvorbis/libvorbis-1.3.7/lib/` 源码子树在包内缺失
  （包内该目录仅剩 AUTHORS/CHANGES/COPYING/README.md 等文档与 libogg 平铺
  文件，`find oggvorbis -name analysis.c` 计 0），无法编译。
- 消费方规避：`JUCE_USE_OGGVORBIS=0`（根 CMakeLists 补丁置位）——
  **功能边界 = 本插件不具备 OGG Vorbis 音频解码能力**；JC303 为合成器
  插件，不加载 OGG 采样/资源，不影响本体功能。
- FLAC 实测未受影响：包内 `flac/` 树完整（`all.h` + `libFLAC/` 全部
  .c 在位，`juce_FlacAudioFormat.cpp` 的 15 个 libFLAC include 目标逐项
  核实存在），`JUCE_USE_FLAC` 保持上游默认 1，不做裁剪。

## SIMD

guitarml RuntimeSIMDLib 对 `-mavx -mfma` 做 CHECK_CXX_COMPILER_FLAG 探测，
aarch64 自动跳过（dsp_accelerated_avx 退化为普通编译）；可用路径为
dsp_accelerated_sse_or_arm（xsimd NEON，__ARM_NEON__ 原生）。

## 上游测试

零测试面（NO_UPSTREAM_TESTS）：归档全树 grep enable_testing / add_test( /
catch2 / gtest / doctest / ctest / unittest 全 0 命中；无 tests/ 目录；
Dockerfile 仅 Debian 11 构建发布产物环境。验证主路径 = test_package
消费式：bundle 布局断言 + dlopen/dlsym 探针（10 项检查，dlclose 独立计数，OHOS 特有新增
用例；kodi-inputstream-adaptive DRAFT lv2-bundle-host-side-test-pattern
同款范式），不带 GUI 运行、不做音频设备初始化（E285 同域先例：无后端环境）。

## C_SIGNALS（高难度工作面，供 Curator）

1. 依赖闭包去网络化：六源（JUCE 改 conan 消费 + 五小件 FETCHCONTENT 注入
   + xsimd 二跳）全部 SHA256 固定，conandata fetchcontent 段即证据。
2. 多格式插件目标（VST3/LV2/CLAP）aarch64 交叉语义：bundle 布局、
   juce_lv2_helper 真机 .ttl 生成、三格式入口符号探针。
3. E505 三深度 $ORIGIN rpath + 全量签名 + NEEDED 闭包断言链。
4. 37 个 JSON 模型（31MB）经 juce_add_binary_data 内嵌 + 两套 GUI 资源
   BinaryData —— 构建体量大（39MB 归档 + JUCE 全模块编译），create 接近或
   超过默认 3600s 时按政策本地扩 build_timeouts（永不入候选）。
5. LTO 去除（3 处）与 SIMD 探测退化路径。
