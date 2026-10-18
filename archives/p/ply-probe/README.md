# ply-probe

> 上游: [iovisor/ply](https://github.com/iovisor/ply) — 轻量级 BPF 动态追踪工具
> 版本: 2.4.0 ｜ 构建系统: autotools ｜ 目标平台: HarmonyOS PC (OHOS 6.0 / aarch64 / clang)

## 简介

`ply` 是一个面向 Linux 的轻量动态追踪工具：以接近 awk/dtrace 的脚本语法编写探针，
内嵌 BPF 编译器把脚本编译为 BPF 字节码，再通过 `bpf()` 系统调用加载到内核执行
（kprobe / tracepoint 前端，事件缓冲区基于 `perf_event_open()`）。

本包产物：`bin/ply`（命令行工具）+ `lib/libply.so`（内嵌编译器/加载器）+ `include/ply/*.h`。

## 适配状态

**状态: built**（本地 `conan create` 全绿，含 test_package 4/4；待 CI release 上传制品仓）

### 已修复的适配问题

| # | 问题 | 处理 |
|---|------|------|
| 1 | tarball 无 `.git` → `git describe` 版本为空 | 补丁 `0001` 在 `AC_INIT` 钉住 2.4.0 |
| 2 | 工具链缺失（本机 `/usr/local/bin` 为坏链） | `tool_requires` 拉取 automake/libtool/bison/flex 并前置 PATH |
| 3 | `config.guess`/`config.sub` 不识别 OHOS 三元组 | 补丁 `0002`/`0003`（须在 `automake --add-missing` 之后应用，E007） |
| 4 | `config.status` 的 `mktemp -d` 目录在 OHOS 不可写 | 配方内禁用 mktemp 分支，走 mkdir 回退（E114） |
| 5 | 链接期 `undefined reference to index/rindex` | 补丁 `0004` 改 POSIX `strchr`/`strrchr` |

### 平台限制（核心结论）

⚠️ **产物可安装可执行，但除 `ply -v` / `ply -h` 外无可用功能路径**——OHOS 未提供内核追踪接口：

| 接口 | OHOS 实测 | 后果 |
|------|-----------|------|
| `bpf()` | **SIGSYS**（信号 31，进程被直接杀死，rc=159；不是 ENOSYS） | 探针无法加载 |
| `perf_event_open()` | `EACCES` | 事件缓冲区不可用 |
| `/proc/kallsyms` | 地址被 `kptr_restrict` 抹零 | kprobe 脚本**编译期**即失败（`ply -e` 静默 rc=1） |
| `/sys/kernel/debug/tracing` | 无后端 | tracepoint 脚本解析失败 |

`ply` 没有降级/替代路径（不存在等价的内核追踪后端），因此**如实声明平台不支持**，
而不是伪造 stub 让它"看起来能跑"。

## 知识图谱扩展

本次适配同时交付知识条目 **E545**（Linux 内核追踪特性在 OHOS 不可用），
含 `prescan_pattern` 字段 → PreScanner 运行时自动派生规则 `PSCAN-KB-E545`，
使同类软件（BPF/kprobe/perf_event/tracefs 族）在**预扫描阶段**即被识别，无需重复踩坑。

## 验证证据

| 文件 | 内容 |
|------|------|
| `2.4.0/reports/test-report.md` | 测试报告（4/4 边界断言 + 平台限制分析） |
| `2.4.0/reports/probe-output.log` | 平台能力探针实测输出（SIGSYS / EACCES / 地址抹零） |
| `2.4.0/reports/ohos-kernel-tracing-probe.c` | 探针源码（无缓冲 + fork 隔离） |
| `2.4.0/reports/repro-kernel-tracing.sh` | 一键复现脚本 |
| `2.4.0/notes.md` | 适配笔记（原理/边界/不适用场景） |

> `reports/` 为 AI 元数据目录，按仓库 `.gitignore` 约定不入版本控制，仅本地留存。
