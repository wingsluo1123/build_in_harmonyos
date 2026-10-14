# E756 — 测试框架版本替换导致 ±inf 断言假失败（googletest 1.14.0 vs 1.15.2）

> 知识库草稿（待主编审核提升为正式条目）。触发任务：xnnpack 0.0-git20241108.4ea82e5
> 适配（平台 rawId 12165），设备实测 2026-10-07。

## 错误特征

`conan create` 内嵌的上游 `ctest -V` 阶段出现大面积"数值断言失败"，但两侧数值其实**完全相等**：

```
/storage/.../src/test/vunary-microkernel-tester.h:147: Failure
The difference between y[i] and y_ref[i] is nan, which exceeds
test_info.Tolerance(y_ref[i], xnn_datatype_of<Out>()), where
y[i] evaluates to -inf,
y_ref[i] evaluates to -inf, and
test_info.Tolerance(y_ref[i], xnn_datatype_of<Out>()) evaluates to 9.9999997473787516e-05.
at 2 / 8, x[2] = -5.20960000000000000e+04
[  FAILED  ] xnn_f16_vlrelu_ukernel__neonfp16arith_u8.negative_slope (3 ms)
...
99% tests passed, 5 tests failed out of 399
```

特征组合（三者同时出现即可判本条目）：

1. 失败行是 `The difference between <a> and <b> is nan, which exceeds …`；
2. 紧跟的 `… evaluates to` 两侧是**同号**的 `±inf`；
3. 失败用例分布在多个不相干的微内核/算子测试二进制里，且**标量**实现也失败
   （排除 NEON/ISA 问题）。

## 触发条件

- 构建系统: cmake（Conan 配方）
- 阶段: testing（上游测试在 `build()` 内真实执行）
- 前置: 配方把上游钉的测试框架 **换成了更旧的版本**（本任务从上游钉的
  `df1544bcee0c…`=1.15.2 换成了仓库里 cpuinfo/ruy 现成的 v1.14.0）

## 根因分析

googletest 1.14.0 的 `DoubleNearPredFormat`（`gtest.cc`）：

```cpp
const double diff = fabs(val1 - val2);
if (diff <= abs_error) return AssertionSuccess();
```

`val1 == val2 == -inf` 时 `diff = fabs(-inf - (-inf)) = NaN`，而 `NaN <= abs_error`
恒为假 ⇒ 断言失败。**被测库并没有算错**：fp16 leaky-relu 在饱和输入
（`x[2] = -5.2096e4`）上把 `x * slope` 溢出成 `-inf`，参考实现同样得 `-inf`。

上游钉的 1.15.2 在 `gtest.cc:1676-1680` 有短路分支：

```cpp
if (std::isinf(val1) && std::isinf(val2) &&
    (std::signbit(val1) == std::signbit(val2) ||
     (abs_error > 0.0 && std::isinf(abs_error)))) {
  return AssertionSuccess();
}
```

所以同一份上游测试在上游 CI（用的就是 1.15.2）全绿；只有"把测试框架换成 1.14.0"
的配方才会大面积假红。xnnpack 实测：62118 条实际运行用例里 116 条失败、5 个
ctest 二进制变红、`ctest` rc=8，其中 594 条断言属于本类（其余 73 条见下节）。

## 解决方案

### 推荐方案：换回上游钉的同一 revision

```sh
# 1) 从上游构建脚本取权威 revision（不要凭"仓库里谁用过"选版本）
grep -rn "googletest/archive" <upstream-src>/cmake/DownloadGoogleTest.cmake
#   → URL …/google/googletest/archive/df1544bcee0c7ce35cd5ea0b3eb8cc81855a4140.zip
#     URL_HASH SHA256=4f45c2213c1ad4de211b15721db4b05c31dc54e244ab26f397345631da327624

# 2) 先核 CMake 兼容性（CMake 4.x 只拒绝 <3.5，1.15.2 声明 3.13 ⇒ 可用）
unzip -p <zip> '*/CMakeLists.txt' | grep -i cmake_minimum_required

# 3) 再核框架确有短路分支（这是判据，不是猜测）
grep -n "isinf(val1)" <vendored-gtest>/googletest/src/gtest.cc
```

本任务按此改 `conandata.yml` 的 googletest url/sha256 为上游钉的 revision 后，
同一批测试的 594 条 nan 断言全部消失。

### 禁止做法

- ❌ 以"仓库里 cpuinfo/ruy 用的是 1.14.0"为先例照搬旧版本 —— 先例不是判据，
  判据是**上游自己钉的 revision** + 该 revision 的 `gtest.cc` 是否有短路分支。
- ❌ 把假红当成平台不兼容，去改配方、裁剪上游测试或把用例记成 SKIP/NOT_RUN 凑绿。
- ❌ 只看 `99% tests passed` 就按"环境噪声"跳过（本次 5 个失败二进制是确定性的）。

## 验证

```sh
# 单二进制复现（修复前必失败、修复后必过）
cd <build_dir>/Release
./f16-vlrelu-test --gtest_filter='*neonfp16arith_u8.negative_slope*'
# 修复前：The difference ... is nan, which exceeds ...（两侧 -inf）
# 修复后：[  PASSED  ] 全过

# 整轮：conan create 内嵌 ctest 的汇总行 + 配方自报的四分项
grep -E "tests passed,|HMBS_UPSTREAM_TEST_RESULT" <create.log> | tail -3
```

本任务修复后实测：`100% tests passed, 0 tests failed out of 399`；
`HMBS_UPSTREAM_TEST_RESULT` = declared_total 62121 / total 62118 /
passed 59822 / failed 0 / skipped 2296 / not_run 3（3 条为上游
`DISABLED_` 用例）。

## 同源陷阱（同一任务里同时命中，一并登记）

同类"测试框架/编译语义差异导致上游测试假红"的第二形态：**aarch64 上 clang 默认
`-ffp-contract=on` 会把 `(a*b)+c` 收缩成 FMA**。XNNPACK 的标量 f32 路径把
`xnn_fmadd_f32(a,b,c)` 写成 `(a*b)+c` 且 `f32-scalar.h` 不定义
`XNN_SIMD_HAS_NATIVE_FMA`，于是有理微内核按"未启用 FMA"的标定常数走
（`vmax_abs_x=5.1158981323`，注释写明该值是插值恰好返回 ±1.0f 的第一个浮点数）；
收缩成 fmadd 后 clamp 点残余 ~3.6e-7，被 `0.5*|x|` 放大后超出
`10*FLT_EPSILON=1.192e-6` 容差（本任务 `f32-vgelu-test` 73 条断言失败）。
处置：对 C/CXX 加 `-ffp-contract=off`（x86/SSE2 基线无 FMA 指令不会收缩，
所以上游 CI 看不到）。判据：失败值 `y=-1.672e-06` vs `y_ref=-0`、容差恰为
`1.1920928955078125e-06`。

## 关联条目

- 与"ISA 相关测试整组 SKIP"类条目不同：本条目是**框架**层假失败，被测代码正确。
- 与"平台不支持某指令集"不同：本条目的失败里标量实现同样失败。
