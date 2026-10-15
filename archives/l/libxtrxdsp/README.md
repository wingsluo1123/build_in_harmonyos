# libxtrxdsp

XTRX SDR 项目的数字信号处理支撑库。提供采样格式转换与 FIR 通道滤波器实现，是 `libxtrx`（XTRX 高层 API 库）收发链路的底层依赖。

## 功能概述

- **采样格式转换**（定点/浮点互转，均为 SIMD 可加速的批量接口）
  - `iq8` / `iq12` / `iq16` 定点 I/Q → `sc32`（float）
  - `sc32`（float）→ `iq16`，`ic16` ↔ `iq16`，`iq8` ↔ `ic8` / `ic16`
  - 交织 / 解交织（interleaved ↔ 分离 I、Q 通道）
- **FIR 通道滤波器**
  - `xtrxdsp_filter_init` / `xtrxdsp_filter_initi`：float 抽头与 int16 抽头两种模式
  - `xtrxdsp_filter_work` / `xtrxdsp_filter_worki`：流式卷积，支持抽取（`decim`，2 的幂）与插值（`inter`）
  - `xtrxdsp_filter_free`：释放 64 字节对齐的状态块
- **滤波器抽头数据**：`g_filter_int16_taps_64_2x`、`g_filter_float_taps_64_2x` 等 2 倍插值半带滤波系数
- **FFT 加速辅助**：`xtrxdsp_fft` 旋转因子与位反转工具

## OHOS 适配

适配工作在 `conanfile.py` 内以 CMake 变量完成，**不修改上游任何源文件，无补丁**。

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| CMake 配置失败：`Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(VERSION 2.8)`，CMake 4.x 已移除 <3.5 兼容 | `CMAKE_POLICY_VERSION_MINIMUM=3.5`（必须是 **cache** 变量，普通变量不进 CMakeCache，压不住下限） |
| 产物缺少 `DT_SONAME`，CI L5a 门禁拒绝 | CMake 无 HarmonyOS 平台模块（E092）：`CMAKE_SYSTEM_NAME=HarmonyOS` 不加载 `Platform/*.cmake`，`CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 为空，上游 `set_target_properties(... VERSION ... SOVERSION ...)` 被忽略 | OHOS 上把 `CMAKE_SYSTEM_NAME` 别名到 `Linux`，恢复完整 Unix/Linux 平台语义（同样使上游 `if(CMAKE_SYSTEM_NAME MATCHES "Linux")` 分支生效，为 `tests/` 目标补齐 `SYSTEM_LIBS`） |
| x86 SIMD 源码是否会误编入 aarch64 | 上游按 `ARCH MATCHES "^x86.*"` 选择 `xtrxdsp_x86_{sse2,avx,avx_fma}.c`，`ARCH` 由 `${CMAKE_C_COMPILER} -dumpmachine` 推导 | aarch64 上 `ARCH="arm"`，x86 源文件不参与编译；`xtrxdsp_config.h` 的 `XTRXDSP_HAS__SSE2__/__AVX__/__FMA__` 由 `#if defined(__x86_64__) \|\| defined(__i386__)` 守卫，aarch64 上未定义，运行时走 `xtrxdsp_*_no` 通用实现。**无需任何源码改动** |

已知差异（与 Linux 相比）：

- OHOS（musl/bionic）下 `rt` / `dl` / `pthread` 属基础 C 运行时，无需显式链接；配方仅声明实际使用的 `m`。
- 通用（非 SIMD）实现是 aarch64 上的唯一路径，性能低于 x86 的 SSE2/AVX/FMA 路径，但结果一致（`test_consumer` 对两者结果等价性做了断言）。
- 上游 `tests/` 两个程序都被安装到 `<lib>/xtrxdsp/`，属测试工具，不通过 `cpp_info.bindirs` 暴露，因此本库**不是**工具包（无 `commands.json`，R38）。

## 依赖关系

- **构建依赖**：CMake ≥ 3.5（实际用 4.x）、clang。
- **运行时依赖**：仅 libm（libc 之外无其他依赖）。
- **被依赖**：`libxtrx`（XTRX 高层 API 库）——`xtrx.c` 调用 `xtrxdsp_init`、`xtrxdsp_filter_*`、`xtrxdsp_iq16_ic16i` 等收发链路核心函数。

## 参考资料

- 源码仓库：<https://github.com/myriadrf/libxtrxdsp>（原 `xtrx-sdr/libxtrxdsp`）
- 项目主页：<http://xtrx.io>
- 许可证：Apache-2.0（见仓库内 `LICENSE`；部分源文件头仍保留迁移前的 LGPL-2.1 文本，以上游仓库 `LICENSE` 文件为权威口径）
