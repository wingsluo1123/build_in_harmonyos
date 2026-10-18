# 手写上下文保存汇编中的 glibc 私有符号依赖

草稿：`DRAFT-ohos-assembly-glibc-private-sigsetjmp`；贡献者 `frj__`；2026-10-17。

修复轮查重基线：main `ad0c1a73eaeeb0807aebf150606a75a9ee950bd0`，2295条正式知识。
`__sigsetjmp`、`sigsetjmp`、`siglongjmp`、`returns_twice`在graph/doc均0命中；
草稿分别1、8、4、0个文件命中，未把全库描述为零命中。
`longjmp`已命中E1279和E1904，边界见后文；查重文件清单见IRAF reports/knowledge-recheck.json。

## 错误特征与适用范围

IRAF 2.18.1 的真实自举工具依赖 `unix/os/zsvjmp.S`。AArch64 分支在保存
状态指针后直接尾跳转 `__sigsetjmp`。用 OHOS SDK 链接时失败：

```text
ld.lld: error: undefined symbol: __sigsetjmp
>>> referenced by zsvjmp.S
```

本条适用于手写汇编直接引用 libc 上下文保存入口的运行时、异常恢复器和协程
实现。输入是链接错误、目标 libc 的符号清单及调用约定；输出是经过行为验证的
最小源补丁和回归证据。没有公开等价 API、闭源目标不可重建、或缓冲 ABI 不同的
场景不能直接套用。

## 为什么相同 AArch64 指令集仍会链接失败

C 调用者包含 `<setjmp.h>` 时可以经过 libc 宏或声明别名分流。`.S` 中手写的
符号名没有经过这一步。IRAF 原分支把 glibc 的导出约定当成了所有非 Apple
AArch64 libc 的约定；OHOS SDK 的可链接入口是公开 `sigsetjmp`。

该问题发生在链接期，添加 include 路径、链接 pthread、设置 TMPDIR 都不会改变
目标 libc 的导出集合。也不能把其他平台的 libc 二进制混入 OHOS 链接。

## 修复与必须保留的 ABI

配方用目标编译器先编译/链接控制程序，再分别探测真实导出符号；不包含setjmp.h，
避免该头的别名隐藏实际被链接的入口。公开sigsetjmp可链接时优先选它，否则仅在
__sigsetjmp确实可链接时使用后者，两者均缺失则失败。通用IRAF_SIGSETJMP定义传入
实际AArch64汇编分支；没有新增OHOS或其它操作系统宏。
保留原有 `str xzr,[x1]`、状态指针存储、`x0 += 8`、`w1 = 0` 和 `b` 尾跳转。
能力缺失只能来自明确的目标符号/声明诊断；资源、执行、权限或同屏额外错误必须失败。
探针直接使用自己的可写临时目录，不依赖外层TMPDIR。

IRAF 的后续 `zdojmp_` 仍调用公开 `siglongjmp`。其第一个缓冲字保存状态指针，
后面才是 libc 的跳转缓冲；必须一起验证，不能只检查 ELF 链接成功。

禁止使用空 `__sigsetjmp` stub；禁止对所有平台无条件替换符号；禁止用已经返回的
普通 C 包装函数保存跳转环境。调用者还须告诉编译器该函数可能返回两次。

### 调用者的编译器契约也必须覆盖生产路径

本次进一步检查发现，手写 C 的声明在 `iraf_kproto.h`，SPP/F2C 生成的 C
却只包含 `f2c.h` 并自行声明 `int zsvjmp_()`。仅在测试程序中写
`returns_twice` 不能证明这两条生产路径正确。因此补丁同时在生产 C 头和
F2C 的源模板 `f2c.h0` 提供兼容声明；后者保留 F2C 的 Subroutine int 返回形式。
实际 clang O2 IR 对照中，未补属性的调用无 `returns_twice`，补后声明和调用
均带该属性，且没有函数类型冲突。

共享状态使用 volatile 读写，并使 `ZSVJMP`、`ZDOJMP` 和恢复目标指针的限定词
一致。这里的 `u_jmpstat` 是静态对象，不能把非 volatile 自动局部变量的 longjmp
规则误当成它的根因；明确的缺口是生产调用者遗漏二次返回属性。

## 决定性对照实验

真机为 HarmonyOS PC / AArch64，使用 SDK clang 15。

| 实验 | 结果 | 证明范围 |
|---|---|---|
| 原始 `zsvjmp.S` + 最小消费者 | `undefined symbol: __sigsetjmp` | 原始符号不可链接 |
| 补丁后真实 `libos.a`，`-O0` | 6/6 | 生产声明与宏各测状态 42、0 映射到 1、负状态 -7 |
| 补丁后真实 `libos.a`，`-O2` | 6/6 | 同一生产声明及宏在优化模式下恢复正确 |
| `llvm-nm libos.a` | `U sigsetjmp`、`U siglongjmp` | 实际库消费公开符号 |
| 独立 libc-test，`-O0` | 4/4 | 标准跳转、零值映射、保存/不保存信号掩码 |
| 独立 libc-test，`-O2` | 4/4 | 公开 API 的优化构建行为 |

实际 IRAF 封装测试位于 `archives/i/iraf/2.18.1/test_package/test_context.c`，
直接链接安装包中的 `libos.a`，包含包内生产头，覆盖直接声明及 setjmp/longjmp 宏。
测试程序不再自行声明 `returns_twice`，避免掩盖实际调用者的契约缺口。
完整运行时的错误恢复另由上游套件和安装后 CL/ECL 消费者检验。

## 独立上游语料及复现

使用 libc-test 的 `src/functional/setjmp.c`，固定到提交
`426ecdcf9eb4ad136069c2db0d357d697a520f62`，并使用同一提交的
`src/common/test.h`、`src/common/print.c`。

来源：<https://github.com/kraj/libc-test/blob/426ecdcf9eb4ad136069c2db0d357d697a520f62/src/functional/setjmp.c>。

```sh
ohos-clang -O0 -I. setjmp.c print.c -o libc-setjmp-O0
./libc-setjmp-O0
ohos-clang -O2 -I. setjmp.c print.c -o libc-setjmp-O2
./libc-setjmp-O2
```

四个 `TEST` 均通过、退出码均 0。`setjmp.c` 的 SHA256 为
`de9320694b8a6bdb2d2145eb7650590184240578dc1a3656a923fb95c096cccf`。
这组独立测试验证公开 libc API 的语义；它本身不调用 IRAF 汇编，因此实际封装
必须由前表另两组 `libos.a` 测试证明，不能互相替代。

## 查重与相邻边界

2026-10-17 修复轮重新核验 main：`ad0c1a73eaeeb0807aebf150606a75a9ee950bd0`，正式graph条目2295。

```sh
git grep -l '__sigsetjmp' <main-tip> -- knowledge/graph knowledge/doc
git grep -l '__sigsetjmp' <main-tip> -- knowledge/drafts
```

正式目录 0 命中；草稿目录有 1 篇 Crystal 预编译自举二进制文章提及此符号。
不能把全知识库写成“0 命中”。该文章处理 glibc 预编译产物不能直接在 OHOS
运行；本条处理可重建源码中的原始汇编调用，并包含尾调用、状态前缀缓冲布局和
信号掩码行为的分别验证。

正式 E1086 已覆盖 glibc 私有类型/宏迁移到公开 C/POSIX 接口的通则，本条不将
该通则另报为新知识。增量是手写汇编绕过头别名、公开入口的尾跳转/缓冲ABI，
以及生产C与SPP/F2C两条声明路径的二次返回契约和验证方法。
E016 的指令集禁用、E462 的ucontext故障定位、E1038 的libpng API迁移均未覆盖此子族。
正式graph/doc中sigsetjmp、siglongjmp、returns_twice仍为0命中；longjmp已有命中。
E1279覆盖libco寄存器槽位/BL/LR及真实SP；E1904用进程内信号与longjmp验证陷阱，
不处理原始上下文汇编的私有libc入口与C/SPP生产声明契约，本条不申报上述既有方案。
KMA草稿中的sigsetjmp/siglongjmp用于已可链接API的信号恢复，也不覆盖此链接/ABI子族。

相邻草稿 `knowledge/drafts/E543-draft-A7F3.kv` 处理libco寄存器槽位、BL与SP恢复，
`knowledge/drafts/ohos-aarch64-conservative-gc-register-roots.kv` 使用公开setjmp保存
待扫描寄存器且不longjmp；二者不覆盖本条的私有libc入口及生产双声明层契约。
这里按完整草稿路径引用；正式E543是libidl2 Autotools条目，不能混同。

`DRAFT-appstream-1.2.0-r05-ohos-openat2-seccomp-sigsys` 与
`DRAFT-E584-bus-sysv-ipc-sigsys-catchable` 使用已经可链接的公开 API 捕获
SIGSYS，修复对象是内核能力探测；本条没有改变系统调用策略。

`DRAFT-BCFF-const-table-rodata-segfault` 已记录 `fpu_control.h` 的头文件问题。
因此本次同遇的 libf2c 头文件分支修复作为复用经验记录，不另报新知识。

## 交付与边界

补丁、安装消费者及上游测试入口均随 IRAF 2.18.1 的同一 PR 提交。
本条不主张所有双下划线函数都有可替代的公开入口，也不主张 libc-test 的
8 项检查等于任意协程实现已经验证。路径 B 是否构成新的通用贡献交评审裁定。
