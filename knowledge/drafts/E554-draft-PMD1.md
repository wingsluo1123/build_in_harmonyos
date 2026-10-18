# E554 — 纯 C 链接含 C++ 目标文件的静态库时缺 libc++

## 错误特征

```
ld.lld: error: undefined symbol: operator new[](unsigned long)
>>> referenced by libaudiofile.a(...)
ld.lld: error: undefined symbol: __cxa_pure_virtual
ld.lld: error: undefined symbol: std::__n1::basic_string<...>::append(...)
```

错误信息里出现 C++ 名字修饰（`_ZdlPv`、`std::__n1::…`、`operator new`）是关键特征。

## 触发条件

- 构建系统: 任意，用 **C 编译器**（clang/gcc）驱动链接
- 阶段: linking
- 依赖: 以静态库形式提供、内部含 C++ 目标文件（如 `audiofile/0.3.6` 的 `libaudiofile.a`）

## 根因分析

某些依赖以静态库形式提供，但库内包含 C++ 目标文件。
纯 C 项目用 C 编译器驱动链接时**不会自动带上 C++ 运行时**，
于是链接报 `operator new[]`、`__cxa_pure_virtual`、`std::__n1::…` 等未定义符号。
在 OHOS（clang + libc++）上运行时库名为 `libc++`（解析为 `libc++_shared.so`），
GNU 平台为 `-lstdc++`。

## 解决方案

### 推荐方案

链接行显式加入 C++ 运行时；对 Makefile 项目用 `LDFLAGS` 传入即可
（make 内建链接规则会带上 LDFLAGS）：

```bash
make -j1 LDFLAGS="-lc++"     # OHOS / clang + libc++
```

### 备选方案

若编译与链接共用同一变量，可让链接步骤用 C++ 驱动（`clang++`）执行；
但用 `clang++` 编译 `.c` 会按 C++ 语义处理源码，需把编译与链接分开，改动较大。

### 禁止做法

- ❌ `-Wl,--unresolved-symbols=ignore-all` / `--allow-shlib-undefined`——把问题推到运行期，启动/加载即崩。
- ❌ `-static-libstdc++` 或手工拷贝 `libc++_shared.so` 到 bin/——违反 R26/R49，污染系统库路径、破坏依赖管理。

## 验证

```bash
nm -C <dep>.a | grep -c ' T *std::'    # >0 说明静态库含 C++ 目标文件
readelf -d <binary> | grep NEEDED      # 应出现 libc++_shared.so
<binary> --version                     # 能加载运行
```

## 关联条目

- 相关: E553（链接期问题）
