# UnitTestMath 固定输入参考值修正

原始 `UnitTestMathSERIAL` 在 `TestDifferenceOfProducts` 的 `dist < 2` 处失败。
该测试用四个 Float32 输入调用补偿乘积差算法，却把参考值写为 `5.376600027084351f`。

## 输入身份与独立参考

| 输入 | 真机测得 binary32 位模式 | 对应精确值 |
|---|---|---|
| a | `4704aa09` | 33962.03515625 |
| b | `c6edcd9a` | -30438.80078125 |
| c | `47225b66` | 41563.3984375 |
| d | `c6c24ff0` | -24871.96875 |

直接解码这四个位模式，以整数/有理数计算，可得
`a*b-c*d = -4926053/65536 = -75.16560363769531`。
此结果本身是精确 binary32，位模式 `c29654ca`。
未先舍入的十进制文本之差为 `26883/5000 = 5.3766`，数值与旧参考值吻合；
这只说明两种输入身份不同，不推断上游作者当年的计算过程。

测试引用的[原作者文章](https://pharr.org/matt/blog/2019/11/03/difference-of-floats)
对同组 float 输入也给出 `-75.1656`，可独立核对。
[fma/exact-oracle.py](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/fma/exact-oracle.py) 使用 Python Fraction 解码实测输入位模式，独立于被测 C++ 算法。

## 编译器、数学库与硬件对照

[fma/probe.cpp](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/fma/probe.cpp) 分别调用 `std::fma`、`__builtin_fmaf` 和 AArch64 `fmadd`，
使用 volatile 输入以避免把整个测试折叠为常量。五种编译设置为
O0、O3、O3+contract off、O3+contract on、O3+no-builtin-fmaf。
每组记录宏、输入位模式、三种调用结果与编译/运行退出码。
这些设置均得到相同的正确结果，不能用关闭 FMA 或浮点收缩解释旧参考值。
这一证据只覆盖本固定向量，不外推所有 libm 或编译器操作都正确。

## 补丁与原断言合同

第一处改动在 `viskores/testing/UnitTestMath.cxx`：将实际 Float32 输入提升到 Float64，
计算两个乘积及差，再转换为 Float32 参考值。对于本固定向量，Float32 到 Float64
提升无损，两个乘积最多 48 位有效数，且两项幅度接近；乘积和差均能精确表示为 Float64。
这不是任意 float 输入都能精确求差的通用保证。

保留原有 `FP_FAST_FMA` guard、`dist < 2`、测试数量和库实现；参考值修正后仍验证同一
补偿运算的 ULP 精度要求。Viskores 消费者另直接验证这一固定向量，并与最终完整
上游结果分开计数。

## 同一注册项内的 Kahan 系数约定

仅修正乘积差后，完整 Math 测试继续在 Kahan 二次式输入处失败。
原始输入 `(94906265.625, 94906267.000, 94906268.375)` 对于本库的
`a*x²+b*x+c=0`，精确判别式为 `-432345576762013751/16 < 0`，返回 NaN 正确，
却与测试期待的两个正实根不符。

[Kahan 原论文](https://people.eecs.berkeley.edu/~wkahan/Qdrtcs.pdf) §1 使用
`A*z²−2*B*z+C=0`，第 5 页 Table 2 给出这三个 A/B/C 数值。因此映射到本库 API
应取 `b=-2*B=-189812534.0`。
[PolynomialRoots 官方示例](https://github.com/giordano/PolynomialRoots.jl#arbitrary-precision)
同样使用这一负系数。这里说明数学约定与 API 的不匹配，不推断作者历史操作。

补丁第二处只改正中间系数及旁注，原两条 `dist < 3` 不变。
改正后 `b=-(a+c)`，多项式精确分解为 `a*(x-1)*(x-c/a)`；判别式 `121/16`，
两根为 `1`、`759250147/759250125`。原第二根 expected 与正确舍入的 binary64
相差 1 ULP，仍符合原阈值，无需顺手改 expected。
两处错误属于同一个 `UnitTestMathSERIAL` 注册项，不能把两次失败运行相加当作新增用例。
仅修乘积差后暴露第二处失败的原始输出见 [math-dop-only-intermediate-output.txt](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/math-dop-only-intermediate-output.txt)；
两处都修正后的完整 Math 输出见 [math-after-output.txt](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/blob/e65190186b41e1b21e069649144a1078d8eb3208/archives/v/viskores/1.1.1/reports/math-after-output.txt)。中间失败没有被覆盖为成功。

```sh
python3 archives/v/viskores/1.1.1/reports/verify-evidence.py --extract <新绝对证据目录>
sh <新绝对证据目录>/fma/run-repro.sh <SDK-clang++> <新绝对工作目录>
```

原始 Math 失败、补丁后的完整 Math 结果和全套结果均随报告保留，具体状态以最终台账为准。
