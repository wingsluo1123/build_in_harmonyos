# W0 report: gcc 16.1.0（GCC 编译器本体 · c,c++ 前端）

> ⚠️ 本文为 W0 阶段快照；下文「libstdc++-v3 可行性未验证」等阻塞点已在本轮
> 全部解决（构建 r10 exit=0 + 全量 testsuite 跑通）。最终结论以 notes.md / W1-analysis.md 为准。

- Issue: 待补（libitm 完整上游测试的前置依赖库；任务清单未提供明确 issue 编号）
- Date: 2026-09-25
- Dependency role: libitm（及 GCC 系列 target library）的上游测试消费编译器。
  提供 `cc1`（C 前端）+ `cc1plus`（C++ 前端）+ libstdc++-v3 + libgcc，
  用于编译 libitm 的 22 个依赖 `-fgnu-tm`/`__transaction_atomic` 的上游测试。

## 上游信息

- 软件：GCC（GNU Compiler Collection）16，编译器本体（C/C++ 前端）。
- 上游：https://gcc.gnu.org/ ，源码 tarball `gcc-16.1.0.tar.xz`。
- 许可证：GPL-3.0-or-later WITH GCC-exception-3.1。
- 版本：16.1.0（与 libitm/libgomp/libgcobol/gcobol 同源；GCC 官方 ftp 无
  gcc-16.1.1.tar.xz，16.1.1 为 releases/gcc-16 分支点）。
- 源码 tarball：`gcc-16.1.0.tar.xz`，sha256
  `50efb4d94c3397aff3b0d61a5abd748b4dd31d9d3f2ab7be05b171d36a510f79`。

## 依赖

### 构建依赖（in-tree，随源码 tarball 一起下载）

| 依赖 | 版本 | 来源 | 结论 |
|------|------|------|------|
| gmp | 6.3.0 | `https://ftp.gnu.org/gnu/gmp/gmp-6.3.0.tar.xz` | ✅ in-tree |
| mpfr | 4.2.2 | `https://ftp.gnu.org/gnu/mpfr/mpfr-4.2.2.tar.xz` | ✅ in-tree |
| mpc | 1.3.1 | `https://ftp.gnu.org/gnu/mpc/mpc-1.3.1.tar.gz` | ✅ in-tree |

（与 gcobol 16.1.0 完全一致的三个 in-tree 依赖，sha256 已实测）

### 构建工具链

- clang/clang++（OHOS LLVM 工具链，作为**构建编译器**编译 GCC 源码，
  同 gcobol/gcc-ada 的「OHOS 无 gcc，用 clang 构建 GCC」路线）。
- llvm-ar/nm/ranlib/ld 等（OHOS 只有 LLVM 工具链，E012）。

### 运行时依赖（本包产物的一部分，非外部依赖）

- **libstdc++-v3**：本包从 GCC 源码树构建。这是与 gcobol 的本质差异——
  gcobol 显式**移除**了 libstdc++-v3（其 configure "cannot run C compiled
  programs" 失败），而 libitm 的 C++ 上游测试需要它。
- **libgcc**：本包构建（gcobol 已验证 `all-target-libgcc` 在 OHOS 可行）。

### 关键不确定性（W1/W5 需真机迭代确认）

| # | 风险 | 说明 |
|---|------|------|
| 1 | **libstdc++-v3 在 OHOS/musl 的构建** | 从未有先例（gcobol 移除、gcc/9.5.0 只做 C）。libstdc++ configure 探测 math/filesystem/gthreads/stdio 等大量 musl 接口，可能逐项暴露 musl 差异（E2175 六类差异） |
| 2 | **cc1plus 链接** | GCC C++ 前端链接 libcommon.a + 后端，gcobol 已验证 cc1 可行，cc1plus 需额外验证 |
| 3 | 完整构建时长 | gcobol notes 明确「all-gcc 接近/超过默认 3600s 窗口」，加 libstdc++ 更久 |

## 依赖数量与结论

```text
依赖数量：3 个 in-tree 构建依赖（gmp/mpfr/mpc，随源码下载，非独立 Conan 依赖）
已满足依赖：gmp/mpfr/mpc 源码、clang/clang++ 工具链
缺失依赖：无外部缺失；libstdc++-v3/libgcc 是本包产物（从 GCC 源码树构建）
是否需要拆分依赖适配：否（gmp/mpfr/mpc 是 in-tree，无需独立 Conan 包）
阻塞点：libstdc++-v3 在 OHOS/musl 的构建可行性未验证（需真机迭代）
下一步：W1 源码分析 -> W2 配方（基于 gcobol 改造）-> 真机 shadow CI
```

## 与已有 GCC 配方的差异

| 配方 | 语言 | libitm | libstdc++-v3 | 用途 |
|------|------|--------|--------------|------|
| `gcc/9.5.0`（gcc-ada worktree） | c | disable | 无 | C 编译器 |
| `gcobol/16.1.0` | c,cobol | disable | **移除** | COBOL 前端 |
| **本库 `gcc/16.1.0`** | **c,c++** | **enable** | **构建** | libitm 测试消费编译器 |

## Decision

以 gcobol/16.1.0 配方为基底改造：`--enable-languages=c,c++`，保留 libitm
（`--enable-libitm` 或去掉 `--disable-libitm`），保留并构建 libstdc++-v3
（不执行 gcobol 的「移除 libstdc++-v3」步骤）。真机 shadow CI 迭代验证。
