# loudgain 0.6.8 测试报告

> **软件**: loudgain（ReplayGain 2.0 命令行工具：FFmpeg 解码 → libebur128 EBU R128 分析 → TagLib 写 ReplayGain 标签）
> **版本**: 0.6.8（上游最后版本，2020-07）
> **测试日期**: 2026-10-09
> **测试环境**: HarmonyOS PC / OpenHarmony aarch64（musl，clang 15，Conan 2.29.1，profile ohos-aarch64）
> **测试类型**: 上游测试套件清点（无）+ 端到端消费者工作流（test_package）

---

## 一、测试摘要

| 口径 | 总数 | 通过 | 失败 | 跳过 |
|:----:|:----:|:----:|:----:|:----:|
| **上游测试套件** | 0 | 0 | 0 | 0 |
| **test_package 消费者断言**（端到端工作流） | 6 | 6 | 0 | 0 |
| **消费者用例通过率** | **6 / 6 = 100 %** | | | |
| **`conan create`** | rc=0 | | | |

**上游测试清点证据（R51）**：上游源码 tarball（v0.6.8 tag 归档，sha256
1137c193…aeaee 已真机核对）**不含任何测试套件** —— 无 tests/、test/ 目录；
CMakeLists.txt 无 enable_testing() / add_test()；文件清点仅
src/、docs/、bin/、cmake/、debian/（docs/images/ 为 README 截图，非测试）。
上游测试 = 0，故"上游测试通过率"无适用口径；适配验证由 test_package
端到端消费者用例承担。

## 二、消费者端到端用例（test_package, 6 断言全过）

test_package 以 conan 消费者身份拉取 `loudgain/0.6.8` 包，对**安装后的**
loudgain 可执行文件执行完整工作流（test_loudgain.sh，纯 POSIX sh）：

1. **version banner** — `loudgain --version` 输出含 0.6.8（二进制启动即验证
   ffmpeg/taglib/libebur128 全部共享依赖解析成功）✅
2. **help banner** — `loudgain --help` 输出含 ReplayGain ✅
3. **噪声 WAV 生成** — 纯 shell（printf RIFF 头 + dd /dev/urandom + cat 拼接）
   生成 16044 字节 8kHz/单声道/16bit 非静音 WAV（无外部 fixture 依赖）✅
4. **扫描 + 写标签** — `loudgain -s i <wav>` rc=0 且输出无 "Couldn't write"：
   FFmpeg 解码 → libebur128 EBU R128 响度分析 → TagLib WAV "ID3 " chunk
   实验性写入（失败仅 err_printf 且 rc 仍为 0，故显式检查输出）✅
5. **结构断言** — 写标签后文件字节数严格增长（TagLib 追加 "id3 " chunk），
   可将静默写失败转化为显式失败 ✅
6. **字节级断言 + 二次运行** — WAV 原始字节（`tr -d '\000'` 剥离 NUL 后）含
   `REPLAYGAIN_TRACK_GAIN` 帧；带预存标签二次运行 rc=0（标签重读路径）✅

**关键实现细节**：
- loudgain 默认 `mode='s'`（skip tags，仅测量不写），写标签必须显式 `-s i` ——
  断言 4/5/6 依赖该参数，否则只测不写（已在脚本与 notes.md 记录）。
- **CI 首跑修复（E265 类工具链差异）**：OHOS toybox grep（/system/bin）把含
  NUL 的文件按二进制跳过，**即使 `-a` 也匹配不到**；本地 GNU grep 能匹配，
  导致本地全过而 CI 断言失败。字节级断言改为 `tr -d '\000' | grep -q`，
  toybox/busybox/GNU 行为一致。

## 三、构建与验证链路

| 阶段 | 结果 |
|---|---|
| lang-preflight (R47) | cpp（C:C++ = 3:1，CMakeLists 声明 C CXX） |
| W0 依赖检查 | libebur128/1.2.6 ✅ taglib/1.13.1 ✅ ffmpeg/4.4.8 ✅（conan download） |
| conan create | rc=0（aarch64-linux-ohos，clang 15） |
| conan-verify | G1–G4 ✅，L2/L4/L5 ✅ |
| W3 本地 CI 模拟 | JC/L0–L5 ✅（junk check incremental 模式通过） |
| test_package | 6/6 断言，HMBS_TEST_PACKAGE_RESULT passed=true |

## 四、OHOS 适配披露

- **pkg-config 不可用**：patch 0001 将 PKG_CHECK_MODULES 块改写为纯
  find_path/find_library，由配方注入 CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH
  （ffmpeg 包为 components 布局，配方聚合 components 的 include/lib 目录）。
- **CMake 4.x 兼容**：上游 cmake_minimum_required(2.8)，配方以命令行
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 通过（toolchain set() 在 CMakeLists
  解析前不生效，须落 -D）。
- **FFmpeg 版本锁定 4.4.8**：scan.c 使用 av_register_all()（FFmpeg 5.0 移除）。
- **taglib 锁定 1.13.1**：上游写死 -std=gnu++11，taglib 2.x 头文件要求 C++17。
- **静态 taglib 的 zlib 链接**：ohpcd taglib 包为静态 libtag.a，其 ID3v2 帧解压
  所需 inflate* 符号由最终可执行文件链接（patch 0001 追加 find_library(z)）。
- 上游无测试套件为事实清点，非跳过；除上述平台性事实外无任何测试跳过项。
