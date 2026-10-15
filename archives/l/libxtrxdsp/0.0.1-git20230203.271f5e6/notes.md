# libxtrxdsp 0.0.1-git20230203.271f5e6 适配笔记

## 编译环境
- 构建系统: cmake（上游为手写 CMakeLists.txt，非 autotools/meson）
- 编译日期: 2026-10-13
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`）
- 目标: HarmonyOS PC aarch64（**原生构建**，build == target == OHOS/armv8）
- Conan: 2.29.1（OHOS 适配版），profile `ohos`
- 状态: built（本地 `conan create` 验证通过；制品仓上传由 CI release 流水线完成 → published）

## 上游信息
- 仓库: <https://github.com/myriadrf/libxtrxdsp>（原 `xtrx-sdr/libxtrxdsp`，已改名/迁移）
- commit: `271f5e60e40dd578c0db5f50ceb7fd6b7119c5ef`（2023-02-03，"Relicensing the code to Apache 2.0 license."）= master HEAD
- tarball sha256: `4fe5c3e5aff5144dff002ec738e37258c63bb68e9fe2f4bb00175932f3d3d77e`
- 许可证: **Apache-2.0**（上游仓库内 LICENSE 全文为 Apache License 2.0）。
  ★ 与同族 libxtrxll 恰好相反：libxtrxll 的 GitHub 元数据标 Apache-2.0 而仓库内 LICENSE 为 LGPL-2.1；
  本库是提交标题明写 "Relicensing the code to Apache 2.0 license."，仓库内 LICENSE 即 Apache-2.0，
  仅部分源文件头仍残留迁移前的 LGPL-2.1 文本。**统一以上游仓库 LICENSE 文件为权威口径**（本库 = Apache-2.0）。

## 为什么做这个包（依赖链上下文）
`libxtrx`（XTRX 高层 API 库，`xtrx.c`）在收发链路上大量调用 `xtrxdsp_*`：
`xtrxdsp_init` / `xtrxdsp_filter_init{,i}` / `xtrxdsp_filter_work{,i}` / `xtrxdsp_filter_free` /
`xtrxdsp_iq16_ic16i` / `xtrxdsp_sc32i_iq16` / `xtrxdsp_iq8_*` 等（共 30+ 处），且上游顶层
`CMakeLists.txt` 用 `find_package(libxtrxdsp REQUIRED)` 强制要求。

适配 `libxtrx` 前做 W0 依赖发布检查（R35 口径：`conan download --only-recipe`，不用 `conan list` 判 binary）实测：

| 依赖 | 制品仓实测 | 结论 |
|------|-----------|------|
| libxtrxll | ✅ `0.0.1-git20201202.1b6eddf` | 已发布 |
| liblms7compact | ✅ `0.0.1-git20190125.bfd5418` | 已发布 |
| **libxtrxdsp** | ❌ `Found 0 pkg/version recipes`（`libxtrxdsp`/`xtrxdsp`/`libxtrx_dsp` 三个名字均已探测） | **缺口** |

按 W0/R36「依赖必须先发布再构建下游」，先适配本依赖库（+0.5 依赖附加分），再回到 `libxtrx`。
另经核对：`liblibxtrxll` 包内只有 `include/xtrxll_*.h` + `lib/libxtrxll.so.0.0.1`，**不含** `xtrxdsp.h`，
二者不可互相替代；上游顶层 CMakeLists 也未引用 `libLMS7002M`（`cmake/FindlibLMS7002M.cmake` 未被调用，
`liblms7002m.h` 由 liblms7compact 提供），故 `libLMS7002M` 非本库依赖。

## 语言预检（R47）
```
expected=cpp, detected=c, 语言匹配（c↔cpp 兼容族）
language_evidence:
  build_system: cmake
  manifest:     CMakeLists.txt project(libxtrxdsp C)
  source_stats: 源文件 11 个（c:11），主体占比 100%
```
exit 0，通过，进入适配主流程。

## 源码结构
```
CMakeLists.txt                 顶层：project(libxtrxdsp C)、SHARED 库、add_subdirectory(tests)、CPack
xtrxdsp.c                      公共入口与运行时 SIMD 分发（cpu_features_init 仅在 x86 分支编译）
xtrxdsp.h / xtrxdsp_config.h   公共 API 与 SIMD 能力宏（后者由 x86 宏守卫）
xtrxdsp_no.c                   通用（非 SIMD）实现入口，内部 #include xtrxdsp_templates.c
xtrxdsp_templates.c            所有转换/卷积模板（不被单独编译）
xtrxdsp_filters.c/.h           FIR 通道滤波器 + 抽头常量
xtrxdsp_filters_data.c         滤波器系数数据
xtrxdsp_fft.c/.h               FFT 辅助
xtrxdsp_x86_{sse2,avx,avx_fma}.c  x86 SIMD 译元（aarch64 上不参与编译）
tests/test_xtrxdsp_sc32i_iq16.c 确定性自校验单元测试（2000 项断言）
tests/test_filter.c             getopt 交互式流式滤波工具（无断言）
```

## 依赖
- 无第三方 Conan 依赖。构建只需 CMake + clang；运行时仅 libm（另 rt/dl/pthread 在 OHOS 属基础 C 运行时）。
- 被依赖方：`libxtrx`（本任务后续目标）。

## OHOS 适配要点（全部在 conanfile.py，**零源码补丁**）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 失败 `Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(VERSION 2.8)`，本机 CMake 4.1.2 已移除 <3.5 兼容 | `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"`（必须是 **cache** 变量，普通 `variables` 不进 CMakeCache、压不住） |
| 2 | 产物无 `DT_SONAME`，CI L5a 门禁拒绝（configure 时 CMake 打印 `System is unknown to cmake, create: Platform/HarmonyOS`） | E092：CMake 无 HarmonyOS 平台模块 → `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 为空 → 上游 `set_target_properties(... VERSION/SOVERSION ...)` 被忽略，不生成 `.so.0` 链 | `os == "OHOS"` 时 `tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"`（+ `CMAKE_SYSTEM_PROCESSOR=aarch64`），恢复完整 Unix/Linux 平台语义；顺带让上游 `if(CMAKE_SYSTEM_NAME MATCHES "Linux")` 分支为 `tests/` 目标填入 `SYSTEM_LIBS` |
| 3 | x86 SIMD 译元会不会在 aarch64 上被编进去 | 上游用 `${CMAKE_C_COMPILER} -dumpmachine` 推导 `ARCH`，仅 `ARCH MATCHES "^x86.*"` 时追加 x86 源文件 | aarch64-linux-ohos → `ARCH=arm`，x86 源文件不参与编译；`xtrxdsp_config.h` 的 `XTRXDSP_HAS__SSE2__/__AVX__/__FMA__` 由 `#if defined(__x86_64__) \|\| defined(__i386__)` 守卫，aarch64 上未定义，运行时打印 `Using generic for xtrxdsp_*`。**无需裁剪/打补丁**（`test_ohos_dsp.c` 对符号集做了断言） |

> 结论：本库在 OHOS 上**不需要任何源码补丁**，`patches/` 为空。适配全部由 CMake cache/普通变量完成
> （R1 参数最少化 / R8 源码修改四不准则 / R3 不手动造 patch）。

## 上游测试清点（R51 三步法 · 第一步）

清点命令与结果：
```bash
ls tests/                                # CMakeLists.txt  test_filter.c  test_xtrxdsp_sc32i_iq16.c
grep -rn "enable_testing\|add_test(" .   # 0 hits（全树无 ctest 注册）
sed -n '1,20p' tests/CMakeLists.txt      # 只有 add_executable + target_link_libraries + install
```
- ctest 注册用例数 = **0**；上游 `tests/` 下共 **2 个测试程序（N = 2）**，两个都由本配方 `build()` 直接驱动运行：
  1. `test_xtrxdsp_sc32i_iq16.c` —— **确定性自校验单元测试**：`F_VALS=1000`，循环内每条样本 2 次
     `CHECK_I`（共 2000 项断言），无硬件/设备/网络依赖。**但上游结尾写死 `return 0;`**，错误只累加到
     `g_errors` 并打印 `Total errors: N` → **退出码不能作为判定依据**，故 `build()` 捕获其输出并断言
     `Total errors: 0`。
  2. `test_filter.c` —— **上游 FIR 滤波流水线**（内部调用 `xtrxdsp_filter_init` +
     `xtrxdsp_filter_work`）。无断言，其**文档化终止方式**是流结束时的短读路径（`return 2` 紧跟
     `read %u`；1 = 滤波器初始化失败，3 = 短写）。故 `build()` 用**2×8192 个 float32 的确定性输入**
     驱动 `-i/-o` 全流水线，断言 ①退出码 = 2（走到文档化流结束路径而非错误路径）；
     ②输出字节数 = 2×8192×4，即满足契约 `out_samples = num_insamples >> decim`（decim=0）。
- 因此「上游测试程序数」= **2**，两者均在本配方 `build()` 中实际运行并各自通过（**2/2 = 100%**）。
  `make check`/`ctest` 在此仓库无内容可跑（注册数 0），故改为直接驱动两个程序并对**各自真正的通过信号**
  做断言（退出码不是通过信号时改断言输出/输出尺寸）。

## 测试（R51 第二步/第三步）

本机 **HarmonyOS PC aarch64 真机**（clang 15.0.4），命令：

```bash
conan create . -pr:h=ohos -pr:b=ohos --build=missing
```

| 测试程序 | 断言数 | 结果 |
|----------|--------|------|
| `build()` 中上游 `tests/test_xtrxdsp_sc32i_iq16` | 2000 | `Total errors: 0` ✅ |
| `build()` 中上游 `tests/test_filter`（2×8192 float32 确定性输入） | 2（退出码=2 + 输出=2×8192×4 字节） | 通过 ✅ |
| `test_package/test_consumer.c` | 47 | 47/47 通过 |
| `test_package/test_ohos_dsp.c` | 26 | 26/26 通过 |
| **上游小计** | **2 个程序** | **2/2（100%）** |
| **test_package 合计** | **73** | **73/73（100%）** |

`test_consumer.c`（消费者集成测试，全部为确定性期望值）：
1–8. `xtrxdsp_sc32i_iq16` 8 项：I/Q 交织顺序 + float→int16 **趋零截断**（+1.5→1、-2.25→-2）
9–10. `xtrxdsp_sc32i_iq16` 的 `scale` 先乘后转（1.5×2→3、-1.5×2→-3）
11–14. `xtrxdsp_sc32_iq16` 4 项（3.7→3、-3.7→-3、0→0、32767→32767）
15–18. `xtrxdsp_ic16i_iq16` 4 项（I/Q 重新交织）
19–26. `xtrxdsp_iq16_sc32` 的 **64 位块路径**（16 字节输入 → 2 个 8 字节块）与
       **尾部路径**（12 字节输入 → 1 块 + 4 字节尾），含 32767/-32768 边界符号
27–30. `xtrxdsp_iq16_sc32` 的 `scale`
31–34. `xtrxdsp_iq16_sc32i` 解交织（I={1,3,5,7}、Q={2,4,6,8}）
35–38. `xtrxdsp_iq16_ic16i` 解交织
39–42. `xtrxdsp_filter_init` 4 项 `-EINVAL` 参数校验（count>64 / inter>2 / decim>6 / max_sps_block<count）
43–46. 滤波器有效初始化、`filter_work` 返回值 = `num_insamples >> decim`、decim=1 时减半、int16 抽头变体
47–50. 1 抽头全通滤波的实际行为：warm-up 段（前 history_size=128 个 float）为 0；
       其后为输入**延迟 128 个 float 的直通**；第二次调用跨块连续性（前 128 个 float = 上一块尾部）；
       `xtrxdsp_filter_free` 清空 `filter_taps` 与 `history_data`

`test_ohos_dsp.c`（鸿蒙特有，26 项）：
1–10. 打包产物符号集：`xtrxdsp_init`、6 个公共转换入口、3 个 `xtrxdsp_*_no` 通用实现经
      `dlsym(RTLD_DEFAULT, ...)` 均可解析 —— 证明测试确实绑定在打包产物上
11–14. `xtrxdsp_sc32i_iq16_sse2` / `_avx`、`xtrxdsp_iq16_sc32_sse2` / `_avx` **必须不存在** ——
       证明 aarch64 上 x86 SIMD 译元未被编译进来
15–20. 公共分发函数与 `_no` 实现结果**逐字节一致**（aarch64 上分发确实落到通用实现），且值正确
21–23. 64 位块加载路径的**小端通道序**：编译期 `__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__` +
       按 lane k 位于 bit[16k,16k+16) 重建 64 位字与宿主读取一致 + 块路径未打乱通道
24–26. `posix_memalign(64)` 的滤波器状态 16 轮 `init`/`free` 循环稳定、抽头被正确复制、free 后指针清空

两个程序均真实链接 libxtrxdsp 并调用其公共符号（R34），CI L1e 破坏性反向验证（移走 lib/ 或 include/）会使本测试失败。

## 关键命令
```bash
# 语言预检
python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight libxtrxdsp 0.0.1-git20230203.271f5e6 --src <源码目录>
# 初始化
OHC_PROJECT_DIR=<worktree> python3 $SKILL_ROOT/scripts/ohc-run.py init-build libxtrxdsp 0.0.1-git20230203.271f5e6 --url=<官方 tarball>
# 本地验证（真机）
conan create . -pr:h=ohos -pr:b=ohos --build=missing
# SONAME 门禁自检
readelf -d <pkg>/lib/libxtrxdsp.so.0.0.1 | grep SONAME   # → libxtrxdsp.so.0
```

## 注意事项
- 本机为 HarmonyOS 真机，`os=OHOS/arch=armv8/compiler=clang 15` 与 CI 一致，故 `conan create` 的结论可迁移到 CI clean 环境。
- 动态库保留 `.so`（非系统同名库，R26 不适用；`ls /lib*/libxtrxdsp*` 无同名项）。
- 纯库包（R38）：包内 `lib/xtrxdsp/` 下的 `test_filter` / `test_xtrxdsp_sc32i_iq16` 是上游 install 规则带来的
  **测试工具**，不通过 `cpp_info.bindirs` 声明，故**不需要** `commands.json`。
- 每次 `conan create` 会在 `test_package/` 下生成 `build/` 与 `CMakeUserPresets.json`，**不入提交**，已清理。

---

### 对话 #1
- 2026-10-13：完成 libxtrxdsp 0.0.1-git20230203.271f5e6 鸿蒙适配（路径 A 基础适配，依赖项角色）。
  查重通过（archives 与制品仓均无 libxtrxdsp）。上游 myriadrf/libxtrxdsp master HEAD 271f5e6（原 xtrx-sdr，已改名）。
  零源码补丁：CMake 4.x policy 下限 + E092 平台别名恢复 SONAME。
  `conan create` 一次通过，上游 test_xtrxdsp_sc32i_iq16 报 Total errors: 0，test_package 73/73 断言通过（消费者 47 + 鸿蒙特有 26）。
  本包为 `libxtrx` 的必需依赖（W0 实测制品仓缺失），按 R36 先行适配发布。
---

**编译结束**: 2026-10-14 20:46
**最终状态**: built
