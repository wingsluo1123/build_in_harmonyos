# DRAFT: JUCE 插件工程作为 conan 包消费方在 OHOS PC 的适配模式（jc303/0.12.3 实证）

- 条目主题：juce_add_plugin 类插件工程（VST3/LV2/CLAP 多格式）在 OHOS PC 上以
  已发布 juce conan 包为依赖做适配与消费式验证的可复用模式。
- 状态：草稿（待知识库主编审核；实证 run：jc303-0.12.3，分支 feat/jc303-0.12.3）
- 先例关联：E092（CMAKE_SYSTEM_NAME=Linux 强制）、E292（FETCHCONTENT_SOURCE_DIR_
  注入）、E468（pkg-config 名映射）、E505（musl 共享库实体化+签名+rpath）、
  E285（无后端环境验证路径）

## 1. 构建期网络去除（FetchContent 六源）

上游插件工程普遍在根/子目录 CMakeLists 用 FetchContent 拉 JUCE 与小件。
无构建期网络时的组合拳：

- JUCE → 消费已发布 conan 包：根 CMakeLists 的 `FetchContent_Declare(juce …)`
  块（含 SOURCE_DIR/SUBBUILD_DIR/BINARY_DIR 行）整体替换为
  `list(APPEND CMAKE_PREFIX_PATH "${JUCE_PACKAGE_DIR}")` +
  `find_package(JUCE REQUIRED CONFIG)`；包前缀经工具链变量注入
  （juce/8.0.5 = INTERFACE 源码分发 + 官方 JUCEConfig + 预构建
  juceaide/juce_lv2_helper/juce_vst3_helper IMPORTED）。
  **JUCEConfig 会设 `JUCE_MODULES_DIR`（CACHE INTERNAL）**，下游
  chowdsp_utils 这类 "if JUCE_MODULES_DIR" 分门别派的库会自动走
  juce_add_modules 路径（不再自己拉 JUCE）。
- 其余 FetchContent 源 → conandata 固定 URL+SHA256 预解包 +
  `FETCHCONTENT_SOURCE_DIR_<UCNAME>` 工具链变量注入（E292）。
  **两个坑（均实测）**：
  1. conan `get(destination=X)` 是"解包到临时目录再 shutil.move 到 X"，
     X 已存在时按 mv 语义嵌套进旧目录 —— submodule 落点必然已存在
     （父归档的空 submodule 目录或前序解包的父目录树），必须先解包到
     `_staging` 再受控 rename；
  2. GitHub 归档不含 submodule 内容，二跳 submodule（clap-libs/clap、
     clap-libs/clap-helpers、RTNeural/modules/xsimd）要用 GitHub API
     `contents/<path>?ref=<commit>` 查 gitlink commit，逐个固定 SHA256
     解包就位，并在 source() 做完整性 marker 断言（marker 表存相对
     deps/ 的完整路径，不要"key+相对路径"拼错）。
- RTNeural 的 `include(cmake/CPM.cmake)` 构建期从 github releases 下载
  CPM 模块：CPM 仅 tests/bench/examples 用（全 OFF），加
  `if(BUILD_TESTS OR BUILD_BENCH OR BUILD_EXAMPLES)` 守卫即可，不改行为。

## 2. 强制 CMAKE_SYSTEM_NAME=Linux（E092，必做）

juce 包内补丁只覆盖 JUCEModuleSupport.cmake 的四处分支（模块源选择/
LINUX=1/linuxPackages 等）。**插件目标侧 JUCEUtils.cmake 仍直接判
`CMAKE_SYSTEM_NAME STREQUAL "Linux"`** 决定 VST3 bundle 布局
（LIBRARY_OUTPUT_DIRECTORY → Contents/<arch>-linux）。不强制时 VST3 退化为
单文件 .vst3，而 POST_BUILD 的 moduleinfo 步骤仍按 bundle 路径
make_directory → 失败。消费方工具链 `tc.variables["CMAKE_SYSTEM_NAME"]="Linux"`
（build==host 设备语义等价）一并消除 "Platform/HarmonyOS unknown" 告警。

## 3. VST3/LV2 POST_BUILD helper 的裸命令名解析

`_juce_add_vst3/lv2_manifest_helper_target` 若未提前存在同名 target 会从
模块源码现建 helper；其 POST_BUILD 以裸命令名调用，make 的 shell 按 PATH
解析 → Error 127。**确定性解法**：消费方 CMakeLists 在 juce_add_plugin 前
预注册 IMPORTED GLOBAL 可执行目标：

```cmake
if(NOT TARGET juce_vst3_helper)
    add_executable(juce_vst3_helper IMPORTED GLOBAL)
    set_target_properties(juce_vst3_helper PROPERTIES
        IMPORTED_LOCATION "${JUCE_PACKAGE_DIR}/bin/JUCE-8.0.5/juce_vst3_helper")
endif()
```

（包内 helper 只 NEEDED libc++_shared.so/libc.so，真机可直接运行。）
注意：recipe 侧 `self.buildenv_info` 修改只向消费方传一跳，对本包自身
build 的 make 子进程无效（PATH 前置方案不可行）。

## 4. moduleinfo.json 可关

`juce_add_plugin(... VST3_AUTO_MANIFEST FALSE)` 跳过 VST3 moduleinfo
POST_BUILD（该步骤 dlopen 刚链接的插件 .so，OHOS 上链路最脆；
moduleinfo.json 为宿主侧可选缓存元数据，插件扫描经模块入口不受影响）。
LV2 的 .ttl 生成（juce_lv2_helper）在同机制下实测可用，保留。

## 5. E505 运行期闭包（多 bundle 深度 + 绝对双保险）

- 插件 .so 的 NEEDED = freetype/fontconfig(+libxml2)/alsa + 系统库；
  X11 为 NOLINK 头依赖不产生 DT_NEEDED。视图物化+逐文件
  binary-sign-tool selfSign（未签名 .so dlopen 即 EACCES）。
- rpath 注入用 **CMAKE_MODULE_LINKER_FLAGS**（插件格式目标是 MODULE 库，
  CMAKE_SHARED_LINKER_FLAGS 不生效——实测踩坑）；
- $ORIGIN 多级条目（覆盖 CLAP 平级/LV2 一级/VST3 Contents/<arch> 四级）
  + 包内视图绝对路径双保险。**注意 link 环节 shell 会展开裸 `$ORIGIN`**
  （cmake_link_script/手工 bash 执行 link.txt 均会剥 $ORIGIN；make 主路径
  实测保留），绝对条目兜底后两种情况都可用。打包后用 readelf 断言
  NEEDED ⊆ 视图∪系统库 且 rpath 非空，防静默失效。
- 产物形态：CLAP 是**目录 bundle**（JC303.clap/JC303.clap 内层二进制），
  VST3 是 JC303.vst3/Contents/aarch64-linux/JC303.so，LV2 是
  JC303.lv2/*.so + ≥2 .ttl（juce_lv2_helper 真机生成）。

## 6. 上游零测试插件的验证主路径

无 CTest/无测试目录的插件工程：test_package 做消费式探针 —— configure 期
file(GLOB) 断言三格式 bundle 布局 + 运行期 dlopen/dlsym（VST3
GetPluginFactory / LV2 lv2_descriptor / CLAP clap_entry），运行时 unset
LD_LIBRARY_PATH（防压过 rpath）。L1e 破坏性反向验证自动成立（lib/ 移走即
失败）。不带 GUI 运行、不做音频设备初始化（E285 同域）。

## 7. juce 包（消费者视角）已知缺陷（报 juce run 修复）

- 已发布 juce/8.0.5 包丢失 vendored **oggvorbis** 源码子树：
  `oggvorbis/libvorbis-1.3.7/lib/` 整棵缺失（包内该目录仅剩
  AUTHORS/CHANGES/COPYING/README.md 等文档与 libogg 平铺文件
  bitwise.c/framing.c，`find oggvorbis -name analysis.c` 计 0），导致
  juce_OggVorbisAudioFormat.cpp 的
  `#include "oggvorbis/libvorbis-1.3.7/lib/analysis.c"` 无法编译 → 下游以
  `JUCE_USE_OGGVORBIS=0` 规避（插件不解码 OGG 资产，功能边界=无 OGG 解码）；
- **flac 树完整、不受此缺陷影响**（Curator tgz 实锤 + 包内核实一致：
  `flac/all.h` 与 `flac/libFLAC/` 全部 .c 在位，
  juce_FlacAudioFormat.cpp 的 15 个 libFLAC include 目标逐项核实存在），
  `JUCE_USE_FLAC` 保持上游默认 1、不做规避；
- JUCEUtils.cmake 的 Linux 分支未随包补丁（见 §2）。
