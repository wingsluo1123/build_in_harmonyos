# libklibc 2.0.14 适配笔记（HarmonyOS PC · 高难度挑战）

## 编译环境

- 上游源码：kernel.org 官方归档 [klibc-2.0.14.tar.xz](https://www.kernel.org/pub/linux/libs/klibc/2.0/klibc-2.0.14.tar.xz)
- SHA-256：`281bfb683e196818412af70b8968b7726475a80ff1c4bd67119e6bf5059f9075`
- 目标设备：HarmonyOS PC，AArch64 / arm64；设备内核报告 HongMeng Kernel 1.12.0
- 构建系统：上游 Kbuild / Makefile
- 编译器与工具：HarmonyOS SDK 26.0.0.18 Clang/LLVM 15.0.4、Perl、Conan 2.29.1
- 状态：2026-10-15 真机完整构建和测试通过

## 适配内容

1. **OHOS UAPI asm 布局**：上游期望标准 `asm-arm64` 目录；HarmonyOS SDK 在 `aarch64-linux-ohos/asm` 发布头文件。补丁 0001 增加 `KLIBCASMDIR` 并将 Kbuild 的符号链接物化改为复制，随后把 Linux、asm 和 asm-generic UAPI 头纳入包。
2. **信号头兼容**：补丁 0002 将 OHOS 内核头使用的 `_KERNEL__NSIG` 映射为 klibc 代码预期的 `_NSIG`。
3. **HMDFS 硬链接限制**：补丁 0003 将共享库 soname 硬链接改为复制，避免设备工作区不支持 hard link。
4. **库包构建范围**：补丁 0004 的顶层 `all` 仅构建 klibc 库本体，跳过 kinit、dash、utils 和 gzip 等不属于 libklibc 的工具。
5. **Clang allocator builtins**：只在 `MAKEFLAGS= make -j1 test` 的编译参数中加入 `-fno-builtin-malloc -fno-builtin-calloc`。Clang 默认 builtins 会改变 `malloctest3` 对 `malloc(0)` 和 calloc 乘法溢出的观测；同一份未修改上游测试在两个 builtin 均关闭后通过。用原始 mmap flags 的单项控制也通过，因此没有保留 `MAP_NORESERVE` allocator 补丁。
6. **HMDFS jobserver 限制**：CI #92893 在 `make -j2` 创建 jobserver FIFO 时收到 `Operation not permitted`，随后递归 Kbuild 产生 `/bin/sh`、`cut`、clang 的 `Resource temporarily unavailable`。配方清除继承的 `MAKEFLAGS` 并对库与测试两个 make 调用都显式用 `-j1`，避免 jobserver FIFO 和并行子进程扇出。

klibc 是 Linux syscall ABI 的 libc 实现，没有可供 HarmonyOS 移植复用的通用 OS 抽象层；本次按路径 C 完成 A、B、C：Conan 配方与真机包测试、配对知识草稿、HarmonyOS 平台移植与全量上游测试。

## 测试结果

最终真机运行使用 Conan `tools.build:jobs=2`；配方内两个 Kbuild 阶段清除 `MAKEFLAGS` 并使用 `-j1`，完整执行所有上游程序：

| 测试集 | 通过 | 失败 | 未构建 | 跳过 |
|---|---:|---:|---:|---:|
| 上游 `usr/klibc/tests` | 39 | 0 | 0 | 0 |
| `test_package` 消费者和 HarmonyOS 探针 | 2 | 0 | 0 | 0 |

Conan 输出：`upstream tests: 39 passed, 0 failed, 0 not-built, skipped=0`；最终 `conan create` 退出码为 0。`test_package` 的两个 `self.run` 程序分别输出 `klibc ok` 与 `MAP_NORESERVE large sparse mapping: PASS`。上游 `testrand48` 按其确定性 seed/rand48 输出向量校验；该程序按设计返回 1，输出匹配时计为通过，没有跳过任何测试，也没有失败项需要豁免。

新增的 `test_package` 程序：

- `test_probe`：以打包的 `crt0.o` 和 `libklibc.a` 静态链接并运行，验证 `strcpy/strcat/strlen/strcmp/printf`。
- `test_ohos_map_noreserve`：使用 HarmonyOS 系统 libc 验证 4 GiB + 1 的稀疏匿名映射与末端触页；这是平台探针，不改变 klibc allocator。

上游 `usr/klibc/tests/*.c` 源码未修改、未删除、未跳过，也没有禁用断言。

## 验证命令

```sh
MAKEFLAGS= make -j1
MAKEFLAGS= make -j1 test EXTRA_KLIBCCFLAGS="--target=aarch64-linux-ohos -fno-builtin-malloc -fno-builtin-calloc"
```

Conan recipe 对每个上游静态测试对象通过 HarmonyOS Clang driver 重链，保留原对象、`crt0.o` 与 `libc.a`，并检查生成 ELF 含设备运行所需的 `.codesign` section。每个上游测试设置 15 秒超时；测试 runner 强制源文件计数为 39，并对失败、未构建和跳过全部阻断打包。

## 交付物

包内提供 klibc 静态/共享库、`crt0.o`、`klcc` 包装器、头文件及许可证。使用 Conan `copy()` 打包，不调用 HarmonyOS 不提供的 GNU `install`。
