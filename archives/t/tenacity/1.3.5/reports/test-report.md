# tenacity 1.3.5 验证报告

## 环境

- OpenHarmony/HarmonyOS PC aarch64（profile `ci/conan/profiles/ohos-aarch64`：os=OHOS 6.0 / armv8 / clang 15 / libc++ / cppstd 17 / Release）
- Conan 2.29.1（OHOS 适配版）
- 宿主 CMake 4.1.2
- 源码: https://github.com/tenacityteam/tenacity/archive/refs/tags/v1.3.5.tar.gz
  sha256 `3bcbbbddf3d7ed9036d5c131c4dd3cc6b037c0888c6b6099c7c149c9dbfcdcb8`

## 构建与打包

- `conan create archives/t/tenacity/1.3.5 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -r=ohpcd`：**exit 0**
  - 9 个 OHOS 补丁全部应用成功（`patch_ng`，Conan 同款）
  - configure：`-- Configuring done (7.5s)`
  - 编译：**105 个 CXX 目标，0 编译错误**
  - `package()`：17 个 `.a` + 113 个 `.h` + `LICENSE.txt`
- 完整包引用：`tenacity/1.3.5#3257adb59f3b0dc980e44269973702b2:c8ca3ba4459c6b4f0c3b3be20197fcf58732672d#9ec5b34100461b834f48601dddeb2275`
- 日志：`reports/conan-create.log`

## 上游测试（如实申报：0/0）

| 项 | 结果 |
|---|---|
| 上游自动化测试总数 | **0** |
| 通过 / 失败 / 跳过 | 0 / 0 / 0 |

技术原因（非未跑，而是上游不存在可运行的测试入口）：

1. 全树 `grep -rn "add_test\|enable_testing\|include(CTest)\|add_custom_target(check"` → **0 命中**，tenacity 1.3.5 未接入 CTest/CMake 测试框架。
2. `tests/` 目录存在（`SequenceTest.cpp`、`SimpleBlockFileTest.cpp`、`ProjectCheckTests/`、`octave/`、`samples/`、`results/`），但**不构成构建或测试目标**：唯一提及它的 `scripts/CMakeLists.txt:43-44` 是传给 `add_custom_target` 的**源码 tarball 打包清单**（配合 `set( TLD "tenacity-minsrc-…" )` 与 `tar.xz`），属打包数据清单，不产生任何测试目标，故 `tests/` 不参与构建。
3. 上述两个测试源引用的 `DirManager.h` 与 `blockfile/SimpleBlockFile.h` 在 1.3.5 源码中**已不存在**（Audacity 时代残留），即便手工加入构建也无法编译。

故上游测试统计如实记为 **0/0**；不以 test_package 的结果替代或冒充上游测试统计。可行性验证由下节新增的 HarmonyOS 消费者用例承担。

## 新增 HarmonyOS 消费者用例（test_package）

真实链接 17 个交付归档 → 真实运行断言 → 归档架构校验。

### 用例 1：`test_tenacity --selftest`（真实 API 调用）

| 分组 | 断言数 | 通过 | 失败 | 跳过 |
|---|---|---|---|---|
| `[lib-math]` SampleFormat 采样格式转换 | 14 | 14 | 0 | 0 |
| `[lib-string-utils]` UTF-8 ↔ wchar_t 往返 | 4 | 4 | 0 | 0 |
| `[platform]` 目标与无头约束 | 4 | 4 | 0 | 0 |
| **合计** | **22** | **22** | **0** | **0** |

`PASSED: 0 failure(s)`。断言明细：

```
[lib-math] SampleFormat 采样格式转换
  ok   : int16 -32768 -> -1.0
  ok   : int16 -16384 -> -0.5
  ok   : int16 0 -> 0.0
  ok   : int16 16384 -> 0.5
  ok   : int16 32767 -> 0.99997
  ok   : int16 1000 -> 1000/32768
  ok   : int16 5 -> 正小数
  ok   : ClearSamples 清零 [1,4)
  ok   : ClearSamples 不影响区间外
  ok   : ReverseSamples 整段反转
  ok   : SAMPLE_SIZE(int16Sample) == 2
  ok   : SAMPLE_SIZE(int24Sample) == 4
  ok   : SAMPLE_SIZE(floatSample) == 4
  ok   : SAMPLE_SIZE_DISK(int24Sample) == 3
[lib-string-utils] UTF-8 <-> wchar_t 往返
  ok   : ToWString 非空
  ok   : wchar_t 宽度使码元数少于 UTF-8 字节数
  ok   : ToUTF8(ToWString(s)) == s
  ok   : 纯 ASCII 往返一致
[platform] 目标与无头约束
  ok   : OHOS PC 为 64 位指针
  ok   : float 采样宽度与 ABI 一致
  ok   : 无 DISPLAY（wxBase-only 消费者不依赖显示服务）
  ok   : 无 WAYLAND_DISPLAY
```

断言取值均由源码推导而非猜测：`CONVERT_DIV16 = float(1<<15)` → `FROM_INT16(s) = s/32768.0f`；`SAMPLE_SIZE(F) = F>>16`；`SAMPLE_SIZE_DISK(int24Sample) = 3`。

### 用例 2：`elf_check`（交付物架构校验）

对全部 **17** 个归档逐一校验 `ar` magic（`!<arch>\n`）与首个 ELF 成员的 `e_machine == EM_AARCH64 (183)`：

```
OK: all 17 archive(s) are ar archives with AArch64 ELF members
```

用例数 17，通过 17，失败 0，跳过 0。

### test_package 结构检查（非反空壳）

`test_package/conanfile.py` 在运行前校验：`licenses/` 非空、17 个 `<lib>.a` 全部存在、17 个 `include/tenacity/<lib>/` 头文件目录全部非空。

## 结论

配方已在 OpenHarmony aarch64 真机环境完成真实构建、打包与消费者验证（消费者 22/22 断言通过，17/17 归档架构校验通过）。上游自动化测试 0/0（附技术原因，如实记录，不以消费者用例冒充）。
