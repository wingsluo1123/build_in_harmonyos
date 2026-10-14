# jitterdebugger 0.3.1-git20200117.b90ff3a 适配笔记

## 上游信息

- 上游仓库：https://github.com/igaw/jitterdebugger
- 固定提交：b90ff3a30e2a0694fd2c61f7f0d2591152f2c2a2
- 下载源：优先使用 gh-proxy 镜像，失败时回退 GitHub
- 上游显示版本：0.3
- 构建系统：Makefile
- 产物：jitterdebugger、jittersamples、jitterplot

## 构建

```sh
make -j1 CC=<OHOS clang>
```

上游没有 `make install`、`make check` 或正式单元测试；Travis 配置只验证
`make` 构建成功。配方在 build() 中保留完整构建，在 test_package 中执行
CLI 的版本/帮助检查，并让 `jittersamples` 解码一个符合上游
`struct latency_sample` 格式的样本文件生成 CSV。

## OHOS 注意事项

jitterdebugger 的实时采样路径会请求 SCHED_FIFO、mlockall 和 tracefs；
这些能力由设备和运行权限决定，不能从普通 CI 环境假定可用。因此消费者测试
不解码“实时调度已成功”的伪结论，而是验证已安装产物可执行、样本格式插件和
CSV 输出链路真实可用。需要在真机进行实时采样时应由具备对应权限的测试任务
单独执行。

OHOS libc 缺少 glibc 的 `pthread_attr_setaffinity_np()`，但提供
POSIX `sched_setaffinity()`。适配补丁在 worker 线程启动后按 `s->affinity`
设置当前线程的 CPU 亲和性，保持每个测量线程绑定单核的上游行为；
该改动只替换等价的内核调度绑定入口，不改变采样算法。

同时 Makefile 为所有源文件统一定义 `_GNU_SOURCE`，使 OHOS sysroot 暴露
`cpu_set_t`；已有源码内的同名宏增加 `#ifndef` 保护，避免重复定义告警。
