# IRAF 2.18.1 机制验证

本文件保留早期独立机制实验记录；完整历史证据固定在公开提交
06b848e36059fb160ce7c925d9ca94abe9d29b16。本轮能力探测实现和24项回归见host-feature-tests.json；
新源码完整W3、生产包符号表、上游及安装/重定位/独立缓存结果见verification.json，
不把历史实验改写为新源码重跑结果。

平台为 HarmonyOS PC / AArch64，SDK clang 15。以下为独立于完整上游套件的补充
实验，不与上游 143 次调用混算。完整配方验收见 test-report.md。

| 对象 | 实测 | 证明边界 |
|---|---|---|
| 原始 AArch64 保存现场入口 | 链接缺失 `__sigsetjmp` | 原汇编引用了目标 libc 不提供的符号 |
| 实际 `libos.a` + 包内同源生产头 | O0、O2 各 6/6 | 直接声明和 setjmp/longjmp 宏，各测试 42、0→1、-7；测试端不自加函数属性 |
| 实际对象符号/反汇编 | `U sigsetjmp`、`U siglongjmp`；四条保存/尾跳转指令 | 不是空 shim；状态指针前缀及 AArch64 JUMP26 尾跳转保留 |
| 真实 SPP → F2C 生成 C | 前后 clang O2 LLVM IR 对照 | 原 C 仅包含 f2c.h；补丁后声明和调用均携带 returns_twice，覆盖生产路径 |
| 独立 libc-test setjmp.c | O0、O2 各 4/4，退出 0 | 公开 API 的普通跳转、零值、保存/不保存信号掩码；不能替代实际 IRAF 封装测试 |
| ECL 隔离重编 | 14/14，完整有序 marker 列表比对 | direct/external、IF/IFERR/IFNOERR、else、procedure、noabort、abort、bye、嵌套任务 |
| F77 构建调度 | 有效双 Fortran 成功；坏 Fortran、坏 CC 参数均非零 | 原编译器实际执行，诊断保留，没有吞掉失败 |
| F2C 构建启动边界 | 11/11故障注入；真机2/2真实F77编译检查 | 仅Popen构造EPERM有界重试；已启动exit1/exit126、信号、wait错误不重试；有效输入生成AArch64对象，坏Fortran即使已有旧C文件仍失败且不产对象 |
| VFN逻辑目录展开 | 原7/9、新9/9；原失败为三层带arch路径及连续空替换 | 复制生产libsys.a，仅替换vfntrans.o并以原ECL对象隔离链接；隐藏旧缓存，保持深度15可用/16拒绝、循环拒绝和输出溢出拒绝 |
| SSH 传输 fixture | 5/5 | 双向数据、独立 stderr、关闭继承描述符、非法参数、同步 exec 错误；未连接远端服务器 |
| `xc -N` / ECL `-i` + `-f` | 两条真实执行路径通过 | 可写临时目录和编译产物复制、初始化脚本拼接 |
| 表合并/图像数组 | 四个输入值保留；8×8 全部 64 像素均为 7；类型拒绝后仍 1 行 | 修复链接冲突之外，还验证数据正确性和拒绝路径 |
| 文件保护 | 3/3 | protect 后 delete 发出警告且文件存在；unprotect 后 delete 移除文件 |

## 独立 libc-test 语料

固定提交：`426ecdcf9eb4ad136069c2db0d357d697a520f62`，仓库
<https://github.com/kraj/libc-test>。使用原始 src/functional/setjmp.c 与
src/common/test.h、print.c，未删测试或替换跳转实现。

| 文件 | SHA256 |
|---|---|
| setjmp.c | de9320694b8a6bdb2d2145eb7650590184240578dc1a3656a923fb95c096cccf |
| test.h | ed618763ddd503dc076f103c4d03c6f03229900f78b7282cf03feb104b58f85d |
| print.c | efb1ccda4d9de7c83528838eb60357b6e4cf82da14dfaf79c3b68ea866da55d7 |

将三个文件放入同一目录，用目标 SDK 编译：

```sh
"$CC" -O0 -I. setjmp.c print.c -o libc-setjmp-O0
./libc-setjmp-O0
"$CC" -O2 -I. setjmp.c print.c -o libc-setjmp-O2
./libc-setjmp-O2
```

## ECL 控制流回归

隔离目录使用生产 libpkg.a/入口对象的副本，以 Bison 3.8.2 从最终 grammar
重生成 ytab.c/ytab.h，同批编译 ytab/builtin/gram/decl 后链接独立 ECL。
已核对 token 定义一致。比对整个有序列表，不能仅检查 marker 是否出现。

| 用例 | 预期且实得顺序 |
|---|---|
| direct_top | BEGIN, HANDLER, AFTER |
| direct_procedure | BEGIN, HANDLER, PROC_AFTER, AFTER |
| external_top | BEGIN, HANDLER, AFTER |
| external_procedure | BEGIN, HANDLER, PROC_AFTER, AFTER |
| if_external | BEGIN, ECHO, AFTER |
| iferr_success_external | BEGIN, ECHO, AFTER |
| iferr_else_external | BEGIN, ECHO, ELSE, AFTER |
| if_else_external | BEGIN, ECHO, AFTER |
| ifnoerr_external | BEGIN, ECHO, NOERR, AFTER |
| noabort_external | BEGIN, AFTER |
| abort_external / abort_direct | 各仅 BEGIN |
| bye | BEGIN, CALLEE, AFTER |
| nested_external | BEGIN, ECHO, MIDDLE, ECHO, AFTER |

这些是上游解释器/grammar 集成缺陷，未证明为 OHOS 或 Bison 专有缺陷。
正式安装消费者另外在实际包入口中检查恢复后的执行顺序。

## VFN 逻辑目录回归

独立缓存的IRAF根路径为100字符。原255字符池在 `noaobin$`→`noao$`→`iraf$`
展开后已使用148字符；`bin(arch)`需再次复制108字符前缀，只余107，遂截断并触发
`SYS_FZMAPRECUR`。相同128字符的绝对文件路径访问/执行均成功，二进制及相对链接一致，
并非ELF或旧缓存路径依赖。

有界池按现有嵌套和路径上限分配；两种push保存分配起点，EOS仅回收弹出的子段。
未提高16层递归、255字符OS目录或511字符输出上限。
实际修复源SHA256：a0bfd517eb5c9f991cf0b8750be0d397caac98c31c8670e2abcce732f1f58507。
原/新矩阵分别7/9和9/9。九项为绝对路径、显式arch、二层arch、三层arch、
220字符目录的80次空替换、深度15、深度16拒绝、循环拒绝、输出溢出拒绝。
最初340字符目录的探针超过上游SZ_OSDIR=255，不属于有效正例；已依据源码改正，
不将该无效探针计入9项回归。
