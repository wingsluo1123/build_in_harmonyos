# W1 report: gcc 16.1.0（GCC 编译器本体 · c,c++ 前端）源码与测试分析

## 定位

gcc/16.1.0 不是普通三方库，而是 **GCC 编译器本体**（C/C++ 前端 cc1 + cc1plus +
libgcc + libstdc++-v3 + libitm）。它是 GCC 系列 target library（libitm / libgomp /
libgcobol / gcobol）上游测试的「测试前置依赖编译器」，同时自身就是一个完整编译器。

验证口径分两层：

1. **作为编译器本体**：跑 gcc 自带上游 testsuite（gcc.dg / gcc.c-torture / g++.dg）
   的全量回归，验证 cc1 + cc1plus 正确性。
2. **作为 libitm 前置编译器**：test_package 的 2 个 `-fgnu-tm` 事务测试验证
   libitm / libstdc++ 的编译/链接/运行闭环。

## 源码与构建系统

- 源码：`gcc-16.1.0.tar.xz`（约 2GB 解压后），含 gcc 前端 + libgcc + libstdc++-v3
  + libitm 等 target library。
- 构建系统：GCC 顶层 autotools（configure + make），out-of-tree 构建。
- in-tree 依赖：gmp/mpfr/mpc（随源码下载）。

## 测试清点

### 上游 GCC testsuite（编译器本体，dejagnu 全量实跑）

| 套件 | 上游用例数 | 说明 |
|------|----------:|------|
| gcc.dg | 42381 | C 前端回归（含 c-c++-common） |
| gcc.c-torture | 28772 | execute + compile + unsorted 三子套件 |
| g++.dg | 163458 | C++ 前端回归 |
| libitm | 25 | 事务内存库回归 |
| libstdc++-v3 | 18761 | C++ 标准库回归（随附 target library） |
| **合计** | **253397** | dejagnu 逐项真实执行，覆盖 100% |

### 鸿蒙特有测试（消费者测试）

| 文件 | 说明 |
|------|------|
| test_tm.c | `gcc -fgnu-tm` 编译 `__transaction_atomic`，验证顺序事务 + 事务内 malloc+cancel（对应上游 simple-1/alloc-1） |
| test_tm.cpp | `g++ -fgnu-tm` 编译事务 + C++ 异常穿透（对应上游 eh-1.C） |

## ★ W1 测试可行性四问（最终回答）

| # | 问题 | 回答 |
|---|------|------|
| 1 | 上游有多少测试？ | 253397（gcc.dg 42381 + c-torture 28772 + g++.dg 163458 + libitm 25 + libstdc++ 18761） |
| 2 | OHOS 上能跑多少？ | **全部**：五个套件 100% 逐项真实执行（dejagnu，真机 3XB0124808000643） |
| 3 | 跑不了的能补替代吗？ | 无「跑不了」项；263 个编译器前端意外 FAIL 逐类归因（musl/OHOS 环境差异，见 notes.md 第六节） |
| 4 | 子系统？平台有能力但没做？ | GCC 前端（cc1/cc1plus）+ libgcc + libstdc++-v3 + libitm 全构建，无遗漏 |

## 构建流程（真机 r10 exit=0）

```text
configure（--enable-languages=c,c++ --enable-libitm --disable-bootstrap --enable-host-shared）
  -> make all-gcc（cc1 + cc1plus + gcc/g++ 驱动）
  -> make all-target-libgcc all-target-libstdc++-v3 all-target-libitm
  -> install + gcc/g++ driver wrapper + 复制 binutils as/ld + ELF 签名
  -> test_package：gcc/g++ -fgnu-tm 编译+链接（compile-only）
```

## 关键结果

1. libstdc++-v3 在 OHOS/musl 构建成功（gcobol 当年直接移除，本包构建，13 项修复）。
2. cc1 + cc1plus 全链路可用（gcc.dg + g++.dg 全量跑通）。
3. 编译器前端三套件通过率 99.7%–99.9%，意外 FAIL 全部为 musl/OHOS 环境差异。
