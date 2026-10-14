# aarch64 上默认量化引擎是 `kX86`：FBGEMM 在 ARM 也报"CPU 支持"，于是默认落到 x86 专用内核并抛 `unknown architecure`

> Draft: DRAFT-PYTORCH-21301-AARCH64-DEFAULT-QENGINE-X86-UNUSABLE
> Stem: `pytorch-2.13.0.1-aarch64-default-qengine-x86-unusable` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-PYTORCH-21301-AARCH64-DEFAULT-QENGINE-X86-UNUSABLE
- **严重度**: 2
- **类别**: platform|quantization|arm64|upstream-defect
- **触发工具**: conan|clang|python
- **阶段**: runtime

## 症状

在 aarch64 上启用 `USE_FBGEMM=ON` 后，**默认**量化路径直接不可用，且报错文字带明显笔误：

```
RuntimeError: unknown architecure          # 注意上游原文拼写为 architecure
```

触发代码（无需用户显式选引擎）：

```python
torch.ao.nn.quantized.dynamic.Linear(32, 16)(torch.randn(4, 32))
```

对照事实（容易让人误判为"打包没打进去"）：

```python
torch.backends.quantized.supported_engines   # ['qnnpack', 'x86', 'fbgemm']
torch.backends.quantized.engine              # 'x86'   <-- 在 ARM 上默认成了 x86
```

即：**引擎确实注册了，但默认选错了**，而选中的那个在 ARM 上算不了。

## 根因分析

上游 `aten/src/ATen/Context.cpp` 决定默认引擎时用的判据是 `fbgemm::fbgemmSupportedCPU()`，
其实现（非 x86 分支）只是 `cpuinfo_initialize()`——**在 aarch64 上返回真**
（FBGEMM 含部分 ARM 支持，所以"支持"这个判断本身不算错），于是默认引擎被设为 `at::kX86`。
但 `kX86` 派发到的 `fbgemm::ExecuteKernelU8S8` 其 arch switch **只处理 x86 的 inst_set**
（avx2 / avx512），遇到非 x86 就走到 `unknown architecure` 分支抛错。

值得注意：上游就在那段代码上方写着注释 `Make it default qengine for X86 CPU platforms`
——**意图本来就是"仅 x86"**，只是判据选得不够严，导致 ARM 被误纳入。

## 判定方法

不要只看 `supported_engines` 就下结论（它只说明"注册了"）。要看**默认值**，并逐个试算：

```python
torch.backends.quantized.engine        # 关键：默认是谁
for e in ("qnnpack", "fbgemm"):
    torch.backends.quantized.engine = e
    try:    torch.ao.nn.quantized.dynamic.Linear(32,16)(torch.randn(4,32)); print(e, "ok")
    except Exception as ex: print(e, "fail:", ex)
```

本例的正确结论是：`qnnpack` 可实际计算，`fbgemm`/`x86` 在该架构上不可计算。

## 处置

把"默认引擎"的判据收紧到 x86（与上游注释的意图一致），非 x86 时回落 QNNPACK：

```c
#if defined(USE_PYTORCH_QNNPACK) && !defined(__x86_64__) && !defined(_M_X64) \
    && !defined(__i386__) && !defined(_M_IX86)
    if (qengine == at::kNoQEngine) qengine = at::kQNNPACK;
#endif
```

权衡如实记录：该修法会让**一例上游 QNNPACK 自身的边界用例**失败（QNNPACK 的
`qnnpack_add()` 显式拒绝空张量，而上游有个用例构造空 `out` 走 channels-last 的
`quantized.add`）。但换来的是量化能力从"任何量化算子都抛 `unknown architecure`、
完全不可用"变为"QNNPACK 可实际计算"，方向正确，且该边界属 QNNPACK 自身能力范围，
不是打包缺陷——**登记它，而不是隐藏它**。
