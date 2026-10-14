# OHOS：解释器进程拿不到可执行内存，运行时 JIT 库（oneDNN/xbyak_aarch64 等）在该进程内不可用

> Draft: DRAFT-PYTORCH-21301-OHOS-INTERPRETER-SANDBOX-NO-EXEC-MEMORY
> Stem: `pytorch-2.13.0.1-ohos-interpreter-sandbox-no-exec-memory` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-PYTORCH-21301-OHOS-INTERPRETER-SANDBOX-NO-EXEC-MEMORY
- **严重度**: 2
- **类别**: platform|sandbox|jit|mac-policy|oneDNN
- **触发工具**: conan|clang|python|cmake
- **阶段**: runtime

## 症状

把 `USE_MKLDNN=ON` 的 libtorch 交给 OHOS 的解释器进程使用时，**第一个真实卷积**就抛异常，而不是精度错误或崩溃：

```
Xbyak::Error: can't protect        (err=6, 即 xbyak 的 ERR_CANT_PROTECT)
```

调用形如 `torch.nn.functional.conv2d(randn(8,3,224,224), randn(64,3,7,7))`：

- 在**解释器进程**里 → 抛上述异常；
- 在**同一个 .so、同一段代码**，由**原生二进制**调用 → 正常返回。

即"库是好的、代码路径是好的，唯独那个进程不行"。

## 根因分析

oneDNN 的 aarch64 内核**不是预先编译好的**，而是由内置的 `xbyak_aarch64` 在运行时生成机器码
（`CodeArray` → `MmapAllocator::alloc()` 申请缓冲，再 `mprotect` 成可执行）。这需要进程具备
"获得可执行内存"的能力。该 OHOS 设备的**解释器进程**（`/data/service/hnp/.../python3`）所在的
沙箱域拒绝这件事，实测（在解释器进程内用 ctypes 直接调 libc）：

| 请求 | 结果 |
|---|---|
| `mmap(PROT_READ\|PROT_WRITE)` | ✅ 成功 |
| `mmap(PROT_READ\|PROT_EXEC)` | ❌ `EINVAL` |
| `mmap(PROT_READ\|PROT_WRITE\|PROT_EXEC)` | ❌ `EINVAL` |
| `mmap(RW)` 后 `mprotect(RX)` | ❌ `EINVAL` |
| `mmap(RW)` 后 `mprotect(RWX)` | ❌ `EINVAL` |

关键对照：**同一个进程 fork 出的原生二进制不受此限**（可 mmap RWX、可执行运行时生成的 stub，
实测返回预期值）。所以这不是内核的 W^X 策略，而是**该进程所在沙箱域**的限制——与同一台设备上
dlopen 被拒的 E212/E488 属同一类"域"限制：**解释器进程是一个受限域，它 fork 出的子进程不是**。

## 甄别方法（3 步，不需要读 oneDNN 源码）

1. **先排除平台级 W^X**：写个原生小程序，`mmap(RWX)` + 执行一段自造 stub。能跑 → 平台允许，
   问题在"谁在问"。
2. **再区分是库还是进程**：同一库、同一调用，分别用原生二进制与解释器进程跑。原生通过、
   解释器失败 → 是进程域限制，不是库缺陷。
3. **看 errno 的性质**：`EINVAL`（而非 `EACCES/EPERM`）说明请求本身被该域判为非法，而不是
   权限位没给够——这也是"再 chmod 一下/换个路径"不会有用的原因。

## 影响面与处置建议

- **影响**：所有依赖运行时 JIT 的库。除 oneDNN（xbyak_aarch64）外，任何自带 JIT/汇编器
  （如 asmjit 的 JIT 模式、LuaJIT、部分 regex 引擎）在解释器进程内都会失败。
- **不受影响**：**构建期**代码生成（PeachPy 生成 C 源、XNNPACK/NNPACK/QNNPACK 的 kernel
  生成都是构建期），以及纯 AOT 内核（ATen native、KleidiAI）。
- **处置**：把该后端在"平台受限"口径下关闭，并**用测试断言把它钉住**（例：
  `assert !at::hasMKLDNN()`），避免后来者无意打开而把可用的基础算子换成不可用的。
  同时保留打包通路（补丁、子模块），使它在允许自修改代码的平台上仍是"改一行"即可启用。
- **不要**试图用 `chmod`、换目录、加 `LD_LIBRARY_PATH` 绕过——被拒的是内存保护请求本身。
