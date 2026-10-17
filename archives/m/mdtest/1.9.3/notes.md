# mdtest 1.9.3 适配笔记

## 编译环境

- 目标：HarmonyOS PC aarch64 / OHOS 6.0 profile
- 编译器：HarmonyOS clang 15，经已发布的 `mpich/5.0.1.2` `mpicc` 驱动
- 构建系统：上游 GNU Makefile
- Conan：2.x
- 状态：`built`；尚未由 release 流水线上传，不能标记为 `published`

## 源码与语言边界

官方 SourceForge 1.9.3 归档 SHA256 为
`b7e76252031232cf0bba91475f48d0c77dd2e0a56a2e871f1d48e6f247109d8a`。
依据 R47 按实际迁移对象和交付产物判定主体语言：生产实现是单个约 3000 行的 C 文件 `mdtest.c`，上游 Makefile 构建并最终交付 AArch64 C ELF；`scripts/` 下三个 Python 文件仅为参数包装、旧版测试驱动和结果处理辅助脚本，不计入交付程序主体。

## 编译步骤

配方应用两个框架生成的补丁，使用 MPICH 包提供的 `mpicc`，并通过 `MPICH_CC` 指向目标 clang：

```sh
make -j1 MPI_CC="$MPI_ROOT/bin/mpicc" MPICH_CC="$OHOS_TOOL_ROOT/clang" \
  MDTEST_FLAGS="-O2 -Wall -Wextra $REPRODUCIBLE_PREFIX_MAPS"
```

最终安装 `bin/mdtest`、man page、README 和许可证。可执行文件去除调试信息后重新签名；消费者测试直接通过已发布 MPICH 的 `mpiexec` 运行安装后的命令。

## 修复内容

| 补丁 | 问题 | 修复 |
|---|---|---|
| `0001-Makefile.patch` | 上游按 `uname` 选编译器但没有 HarmonyOS 条目 | 增加 `CC.HarmonyOS=${MPI_CC}`，不注入平台宏 |
| `0002-mdtest.c.patch` | 屏障模式先在各 rank 计算局部速率，汇总时再取最大速率，等价于采用最快 rank 的时间 | 对阶段耗时执行 `MPI_Allreduce(..., MPI_MAX, testcomm)`，再用总操作数除以关键路径耗时 |

两个补丁由 `refresh-patch --auto` 生成后仅收窄上下文以避开上游既有行尾空格；语义差异未改变，并按顺序在官方干净源码上通过 `patch --dry-run --fuzz=0 -p1`。

## 上游测试清点（R51）

| 来源 | 静态清点 | 实际执行 | 结果与归因 |
|---|---:|---:|---|
| `scripts/tester.py` 参数矩阵 | 39 | 39 | 30 个正向成功；8 个多路径但未启用 `-u` 的组合以明确的参数互斥诊断退出；1 个干净目录 `-r` 维护场景以上游未创建前置对象的明确删除失败诊断退出 |
| `mdtest -h` | 1 | 1 | 成功 |
| **合计** | **40** | **40** | **31 个正向成功，9 个预期负向结果，0 个未分类失败** |

原 runner 是 Python 2 脚本，硬编码 `/panfs`，且只记录子进程输出而不校验退出码。消费者测试没有篡改参数语义：它将目录换为可写临时路径，以 Python 3 逐项重放全部 39 个参数组合。正向场景要求正常结束并输出摘要；负向场景每次都要求非零退出，并在 MPICH 的 `MPI_Abort` 偶发截断诊断时进行最多三次有界重放，至少一次观察到对应的缺失对象或参数互斥诊断。40 项均已执行和归因，其中 31 项正向成功、9 项确定性负向、0 项未分类失败；不把负向退出表述为上游 PASS。

## 新增验证

- 一个完整的 HarmonyOS 目标端消费者场景：执行 Conan 安装后的已签名 AArch64 `mdtest`，通过已发布 MPICH 的真实 `mpiexec` 建立 2-rank communicator，在目标端临时目录完成文件创建阶段；起始 barrier 后、rank 1 的文件创建起始采样前注入一秒调度偏斜，要求正式 CLI 汇总吞吐落在 `0 < rate < 12`。延迟探针同时输出被命中的 rank、调用序号和时长；回退补丁会稳定恢复为数千 ops/s 并失败。
- `-B` 无屏障模式继续验证本地速率为正，确保修复没有改变该模式的上游语义。
- 五个 HarmonyOS 制品断言：ELF、AArch64、`.codesign`、`libmpi.so.12` 闭包、无 Conan cache 路径。
- 共 47 个外部可观察结果：40 个上游场景结果 + 1 个新增跨平台行为预言机 + 1 个 HarmonyOS 目标端完整消费者场景 + 5 个目标制品预言机。

## 已发布依赖

- `mpich/5.0.1.2`：OHOS armv8 recipe revision `6f27d84073930139fadac21a6e8b37ef`，package ID `783062abfdc1764333d0178d0c88145bad0e32a7`。

## 交付边界

本次在真实 HarmonyOS PC 上以同一 MPICH 安装执行多进程和多路径矩阵。它验证 MPI communicator、rank、barrier 和本机多个目录的调度语义；不宣称完成跨物理节点文件系统性能标定。后者需要独立集群和共享文件系统，是部署规模边界，不影响命令、MPI 协调和关键路径统计正确性。

---

**编译结束**：2026-10-16 03:56 UTC
**最终状态**：built
