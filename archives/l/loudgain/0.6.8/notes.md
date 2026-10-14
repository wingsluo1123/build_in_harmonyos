# loudgain 0.6.8 — 适配笔记 (HarmonyOS PC / OHOS aarch64)

## 上游概况

- 项目: https://github.com/Moonbase59/loudgain (v0.6.8, 2020-07, 上游最后版本)
- 语言: C 为主 + 1 个 C++ 源文件 (src/tag.cc, lang-preflight 判定 cpp, c↔cpp 兼容族)
- 构建系统: CMake (cmake_minimum_required 2.8)
- 类型: CLI 应用 (package_type=application)，产物 `loudgain` 可执行文件 + 辅助脚本 `rgbpm`
- 许可: BSD-2-Clause

## 上游测试清点证据 (R51 三步法 第一步)

- 上游源码 tarball **无任何测试套件**：无 tests/、test/ 目录；CMakeLists.txt 无
  enable_testing()/add_test()；tarball 文件清单仅 src/、docs/、bin/、cmake/、debian/
  (docs/images/ 下是 README 截图，非测试)。**上游测试 = 0**。
- 因此适配验证 = test_package 端到端消费者用例 (1 项新增, OHOS-specific)：
  纯 shell 生成噪声 WAV → loudgain 扫描写标签 (FFmpeg 解码 + libebur128 分析 +
  TagLib 写入, 并检查输出无 "Couldn't write") → 结构断言 ID3 chunk 使文件增长 →
  NUL 剥离后字节级断言 REPLAYGAIN_TRACK_GAIN 已写入 → 二次运行验证标签重读路径。
  共 6 项断言。
- **CI 首跑踩坑 (E265 类工具链差异)**: OHOS toybox grep (/system/bin) 把含 NUL
  的文件按二进制跳过, **即使加 -a 也匹配不到**; 本地开发会话的 GNU grep 能匹配,
  导致本地 5/5 全过而 CI 断言 4 失败。修复: 字节级断言改为
  `tr -d '\000' < file | grep -q`, toybox/busybox/GNU 行为一致。

## W0 依赖发布检查 (全部已发布到 ohpcd)

| 依赖 | 版本 | 验证方式 |
|---|---|---|
| libebur128 | 1.2.6 | conan download -r=ohpcd --only-recipe ✅ |
| taglib | 1.13.1 | conan download ✅ (选 1.x: 上游写死 -std=gnu++11, taglib 2.x 头文件要求 C++17) |
| ffmpeg | 4.4.8 | conan download ✅ (FFmpeg 5+ 移除 av_register_all(), scan.c 仍在用; 4.4 为未打补丁可编译的最新系列) |

- libmp3lame **不是** loudgain 直接依赖（README 提及系历史原因）：解码全部经 FFmpeg
  （其 conan 包自身拉 lame），打标签经 TagLib。CMakeLists.txt 只链接
  avcodec/avformat/swresample/avutil/taglib/ebur128。

## OHOS 适配点

1. **pkg-config 不可用** → patch 0001 把 PKG_CHECK_MODULES 块改写为纯
   find_path/find_library，由配方注入 CMAKE_INCLUDE_PATH / CMAKE_LIBRARY_PATH
   (ffmpeg 包是 components 布局，配方遍历 cpp_info.components 聚合各组件目录)。
   taglib 头文件在 <prefix>/include/taglib/ 而源码是扁平 include (<taglib.h>)，
   find_path 用 PATH_SUFFIXES taglib。
2. **CMake 4.x 拒绝 cmake_minimum_required(2.8)** → 配方设
   CMAKE_POLICY_VERSION_MINIMUM=3.5 (cache 变量, 同 taglib 1.13.1 配方先例)。
3. **SET(CMAKE_C/CXX_FLAGS ...) 覆盖式赋值**会丢掉 conan 工具链标志 → patch 0001
   改为追加 (${CMAKE_C_FLAGS} ...)。
4. HAVE_PTY_H: OHOS musl 提供 pty.h，config.h 探测正常；printf.c 有条件编译兜底，无风险。
5. 源码 URL 用官方 GitHub tag 归档 (codeload)，sha256 真机核对；无 gh-proxy 残留。

## 构建记录 (W3)

- 见 test_results / manifest.yaml（conan create rc=0, test_package 6/6 断言通过;
  CI 首跑 5 断言版在 toybox grep 二进制匹配差异上失败, 修复后复跑）。
---

**编译结束**: 2026-10-09 21:00
**最终状态**: published
