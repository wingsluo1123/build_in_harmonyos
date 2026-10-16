# DRAFT-mjs-2.9.0-aarch64-double-int32-conversion-ub — double→int32 转换 UB 经 int64_t 中转修复

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-29
> **Severity**: 🟡 medium | **Category**: portability / aarch64 / runtime-safety / compilation

## 相关既有条目（同族差异化定位）

本 skill 与既有 "int32 收窄/双重转换" 及 "大数/浮点存储" 条目共享数值转换背景，但本条目是
**把负数 double 直接转为 uint32/int32 触发的 C 标准 UB 在 aarch64 上产生可观测错误**
（无符号右移负数坍缩为 0、`mjs_get_int` 负值错读），经 `int64_t` 中转修复——非重复条目；
申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E432**（native-api-contract） | 正式收录 | native API 输出所有权 + 坐标收窄（synergy-core） | 非本题——那是 **资源所有权与坐标边界检查**；本条目是 **C 语言 double→整型转换 UB**（负数 double 转 uint32/int32） |
| **E419**（signed-char） | 正式收录 | plain char 符号性 | 非本题——char 符号，非 double→整型转换 |
| **DRAFT-lunasvg-3.5.0-plutovg-bgra-pixel-layout** | 草稿 | little-endian 像素字节序 | 非本题——字节序，非数值转换 UB |
| **DRAFT-wide-integer-1.01-long-double-mantissa-storage** | 草稿 | long double（IEEE quad）尾数存储 | 非本题——大浮点存储，非 int32 收窄 UB |
| **DRAFT-ohos-statx-musl-compat** | 草稿 | statx syscall 接口补全 | 非本题——接口缺失，非数值转换 |

> 全库查证（2026-09-29，只读快照 head 317e16ed）：formal E*.kv 541 条 + draft 1690 条
> 中 `mjs`/`urshift`/`double.*int32`/`uint32.*int64`/`negative.*shift` 仅命中上述同族
> 条目；`(uint32_t)(int64_t)`、`mjs_get_int`、`TOK_URSHIFT` 路径 0 条——无正面撞车；
> 本条目为真增量。

## Scope（何时用）

在 aarch64（HarmonyOS PC / ARM64）上用 clang 编译、把 **负数（或超出 uint32 范围）double
直接强制转换为 uint32/int32** 的嵌入式 C/C++ 库（JS 引擎、数值解释器、FFI 桥接类），
出现：

- `(uint32_t) da` / `(unsigned int) get_double(v)` 直接收窄负数 double；
- 无符号右移（`>> >`）负数运算结果坍缩为 0；
- `mjs_get_int`/`mjs_get_int32` 对负值返回错误结果。

典型实例：cesanta/mjs 2.9.0（`TOK_URSHIFT` 分支与 `mjs_get_int()`）。

## Symptom

```text
# JS: (0-14) >>> 2
期望 1073741820，aarch64 上实际得到 0（负数 double 强转 uint32 后坍缩）
# C: mjs_get_int(mjs, 0-14)
期望 -14，aarch64 上因 (unsigned int)get_double(v) 的 UB 得到错误值
```

## Root Cause

1. C 标准（C11 6.3.1.4）：实浮点转换为整型时，若值无法由整型表示，行为未定义
   （UB，而非实现定义）；**负数 double 转 uint32 必然越界 → UB**；
2. `(uint32_t) da`（`da` 为负 double）在 x86 上恰好得到按位回绕结果，掩盖了 UB；
   在 aarch64 上 clang 生成 `fcvtzu` 等饱和转换指令，直接把负数坍缩为 0——
   同源 UB 在不同架构产生**可观测差异**；
3. `(int)(unsigned int) get_double(v)`（mjs_get_int）同理：先转 unsigned int（负值 UB），
   再由 int 收窄，aarch64 上负值被错误截断。

## Recommended Solution

**主方案：经 int64_t 中转再收窄。**

```c
/* 无符号右移：先把 double 阶段性地落到 int64_t，再取低 32 位 */
case TOK_URSHIFT: return (double) ((uint32_t) (int64_t) da >> (uint32_t) (int64_t) db);
/* mjs_get_int：double → int64_t → uint32_t → int（首步在最宽有符号类型内是定义良好的） */
return (int) (uint32_t) (int64_t) get_double(v);
```

理由：IEEE double 总能由 int64_t 表示其整数值（int64 覆盖 ±2^63，double 尾数 52 位），
`(int64_t)` 转换在值域内定义良好；之后的 `uint32_t`/`int` 收窄仍保留负值补码语义，
不再触发"负数转无符号"UB。

## Verification

```bash
# 上游单测（本地 harness 补全缺失的 common/test_main.h，非交付物）
cd <src> && conan-run unit_test_v2    # 42 tests, 3436 checks 全部通过
# test_package 消费者测试（OHOS aarch64 profile，conan create 内执行）
./test_mjs                            # "mjs consumer test passed"
# 专项断言
(0-14) >>> 2 == 1073741820
(0-14) >> 2  == -4
mjs_get_int(0-14) == -14
```

## Applicable Boundary

- 适用于**值域内**（|v| ≤ 2^31 且为整数值）的 double→int32/uint32 收窄；对超出 int64
  表示范围的浮点需另行检查；
- 本 patch 属于可移植性修复，不改变取值语义：修复前 x86 恰好得到补码结果，
  修复后 aarch64 与 x86 一致；
- FFI 回调/大整数（>2^53）落在本条适用边界之外。

## Counterexamples / Limitations

- **反例（禁止盲改）**：不应对合法 uint32 语义的 `(uint32_t) positive_double` 一律加
  int64_t 中转——正值转换本就定义良好，改成两步转换反而引入不必要的实现依赖；
- 仅在**可能为负**（减法、取反、无符号右移操作数）路径上中转；
- 不能把"替换为 `llrint`/`lround`"当作等价修复：它们有舍入/异常语义，会改变 mjs
  的位运算语义（按位截断而非舍入）。