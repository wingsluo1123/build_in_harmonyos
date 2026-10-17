# mdtest 1.9.3 测试报告

> 日期：2026-10-16
> 目标：HarmonyOS PC aarch64，MPICH 5.0.1.2，2/4 rank 真实多进程执行

## 结果摘要

| 类别 | 清点 | 执行 | 符合预期 | 未分类失败 |
|---|---:|---:|---:|---:|
| 上游 runner 参数与帮助场景 | 40 | 40 | 31 正向成功、9 确定性负向 | 0 |
| 新增跨平台行为预言机 | 1 | 1 | 1 | 0 |
| HarmonyOS 目标端消费者场景 | 1 | 1 | 1 | 0 |
| HarmonyOS 制品预言机 | 5 | 5 | 5 | 0 |
| **总计** | **47** | **47** | **47** | **0** |

上游 40 个结果由 31 个正向成功和 9 个确定性负向结果组成。八个负向结果是未启用 `-u` 的共享目录多路径组合，消费者要求它们以明确的参数互斥诊断退出；另一个是干净目录上的 `-r` 维护调用，上游 runner 没有创建其前置对象，消费者要求它以明确的缺失对象删除诊断退出。MPICH 在 `MPI_Abort` 时可能截断某个进程的诊断，因此负向场景每次仍须非零退出，但允许最多三次有界重放以取得一次精确错误类别；三次都没有对应诊断即失败。原 runner 不检查子进程状态，因此这里报告的是“40/40 已执行并完成归因”，不是“上游 40/40 PASS”。

## 最终真机输出判定

```text
UPSTREAM_SCENARIOS_OBSERVED=40/40
UPSTREAM_POSITIVE_PASS=31 UPSTREAM_NEGATIVE_CLASSIFIED=9
CRITICAL_PATH_RATE in (0, 12)  # 本次约 8 ops/s
HARMONYOS_CONSUMER_SCENARIO_PASS=1/1
HARMONYOS_ELF_ASSERTIONS_PASS=5/5
CONSUMER_ASSERTIONS_PASS=7/7
```

关键路径实验为 2 ranks、每 rank 4 个文件创建操作。rank 1 在起始 barrier 返回后、采集文件阶段起始时间并执行首个生产操作之前延迟一秒；探针输出确认命中 `rank=1 wtime_call=3`。rank 0 已进入生产阶段并最终在结束 barrier 等待，理论聚合吞吐约为 `8 / 1s = 8 ops/s`，最终结果与关键路径一致。

该关键路径实验是一个完整的 HarmonyOS 目标端消费者场景：它执行 Conan 安装后的已签名 AArch64 `mdtest`，通过已发布 MPICH 的真实 `mpiexec` 创建 2-rank communicator，在目标端临时目录完成文件创建阶段并解析正式 CLI 汇总输出。签名 PMPI 探针只制造受控调度偏斜，不替代被测生产程序、MPI collective 或文件操作。另一个新增行为预言机独立验证 `-B` 无屏障语义。

## 制品检查

- 安装后的 `mdtest` 是 AArch64 ELF，并含 `.codesign`。
- 动态闭包包含 `libmpi.so.12` 和系统 `libc.so`，无 `RPATH/RUNPATH`。
- ELF 不含 `.conan2/` 或构建/包缓存路径。
- 消费者测试使用包内命令和已发布 MPICH 的真实 `mpiexec`；延迟库只在起始 barrier 与首个生产操作之间制造一个 rank 的调度偏斜，不替代 mdtest 的生产归约实现。

## 证据口径

原始日志和实验 ELF 保存在仓库外，不提交个人路径或二进制。仓内保留配方、补丁、完整 runner、延迟探针源码、命令和判断标准，可在相同 Conan 图上重建。路径 B 的三臂摘要和对象哈希见 `path-b-evidence.md`。

```text
最终 mdtest ELF   f0a89a43aea34f76a46e3fe727a87613a8d5a435d9e8d501159dfa373c16e9b4
签名延迟探针 ELF  ccb09bc54329649011615db6df2df9389a2d7a71b023303f57ccf836b1f76076
正式 W3 日志       由 finish 生成的本地 .ci-result.json 与 W4 审计共同绑定（日志不入仓）
```
