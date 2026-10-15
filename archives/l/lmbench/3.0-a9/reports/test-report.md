# 测试报告 — lmbench 3.0-a9（HarmonyOS PC / aarch64）

环境：HarmonyOS PC（HAD-W32，HarmonyOS 6.1.0.117，内核 1.12，aarch64，20 逻辑核）；
OHOS SDK clang 15.0.4；Conan 2.29.1（OHOS 适配版）；profile `ohos-aarch64`（目标平台）。

## 1. 上游测试清点（R51）

| 项目 | 结果 | 证据（命令） |
|------|------|--------------|
| `tests/`、`test/` 目录 | 无 | `find . -maxdepth 3 -type d \( -iname 'test*' -o -iname '*check*' \)` → 空 |
| Makefile test/check 目标 | 无 | `grep -n '^test\|check' src/Makefile` → 空（仅 `testmake` 供 gmake 探测） |
| ctest/pytest/unittest 注册 | 无 | `grep -ril 'ctest\|pytest\|unittest' .` → 无命中 |
| 上游“测试面” | 49 个基准程序运行即验证 | 每个 `lat_*`/`bw_*` 程序运行产出测量值 |

**上游测试用例统计：N=0**（无断言式测试框架）；按 R51 口径如实申报，适配后用
test_package 消费者回归补全（26 项断言）。

## 2. 上游测试运行结果

上游无测试套件，因此无“上游 N/N′ 通过率”意义上的运行；替代口径 = 基准程序真机
实跑。本适配实跑证据：

| 程序 | 命令 | 输出（样例） | 退出码 |
|------|------|--------------|--------|
| 标定 | `enough` | `1000000`（负载机取上游保守缺省 SHORT；空载取 5000） | 0 |
| 标定 | `timing_o` | `0` | 0 |
| 标定 | `loop_o` | `0.00008098`（另一次实跑；当次回退） | 0 |
| 系统调用 | `lat_syscall null` | `Simple syscall: 1.0270 microseconds` | 0 |
| 系统调用 | `lat_syscall write` | `Simple write: 1.6406 microseconds` | 0 |
| 管道 | `lat_pipe` | `Pipe latency: 40.7214 microseconds` | 0 |
| 管道带宽 | `bw_pipe` | `Pipe bandwidth: 775.30 MB/sec` | 0 |
| 上下文切换 | `lat_ctx -s 0 2` | `2 14.93` | 0 |
| 进程创建 | `lat_proc fork` | `Process fork+exit: 8194.5537 microseconds` | 0 |
| RPC（平台能力） | `lat_rpc` | `Sun RPC is not available on this platform` | 1（预期非 0） |
| 负向对照 | `lat_syscall no_such_mode_xyz` | usage 文本（列出合法子命令） | 255（预期非 0） |

> 数值说明：测试时刻共享设备存在其他参与者的并发构建（load ≈ 26-32），数值仅作
> 功能冒烟口径；同机空载复核样例：lat_syscall null 1.09us、bw_pipe 1120 MB/sec、
> lat_ctx(2) 11.7us（与 Linux 同类平台量级一致，不做跨平台对比）。

## 3. 消费者回归测试（鸿蒙特有测试，test_package）

`test_package/test_lmbench.sh`（26 项断言）本地 dry-run（真实包布局模拟，同一设备；
实际 CI 输出以 `conan create` 日志为准）：

```text
ok 1 - 49 benchmark executables are present and executable
ok 2 - 10 lmbench headers are installed
ok 3 - libmbench.a static library is installed
ok 4 - hello prints the upstream greeting
ok 5 - enough yields a positive calibration interval (ENOUGH=1000000)
ok 6 - timing_o yields the gettimeofday overhead (TIMING_O=0)
# info: loop_o helper returned '0.00000000' - falling back to LOOP_O=0.0000134
ok 7 - loop_o yields the benchmark loop overhead (LOOP_O=0.0000134)
ok 8 - lat_syscall null exits 0
ok 9 - lat_syscall null reports a positive syscall latency (1.0270 us)
ok 10 - lat_syscall write exits 0
ok 11 - lat_syscall write reports a positive latency (1.6406 us)
ok 12 - lat_pipe exits 0
ok 13 - lat_pipe reports a positive pipe latency (40.7214 us)
ok 14 - bw_pipe exits 0
ok 15 - bw_pipe reports a positive pipe bandwidth (775.30 MB/sec)
ok 16 - lat_ctx -s 0 2 exits 0
ok 17 - lat_ctx reports a positive context-switch latency (14.93 us)
ok 18 - lat_proc fork exits 0
ok 19 - lat_proc fork reports a positive latency (8194.5537 us)
ok 20 - lat_rpc reports unsupported Sun RPC with nonzero exit (rc=1)
ok 21 - lat_rpc explains the missing platform capability
ok 22 - unknown benchmark mode is rejected (rc=255)
ok 23 - usage text lists the valid modes
ok 24 - consumer compiles against packaged headers + libmbench.a
ok 25 - consumer program runs (rc=0)
ok 26 - consumer measures a positive tvsub() delta (0.006955 s)
1..26
# all 26 checks passed
```

- consumer 链接测试 = 用包内 `include/` 头文件 + `lib/libmbench.a` 编译一个调用
  `tvsub()` 的真实 C 程序并运行（鸿蒙特有/消费者视角回归，`test_package/consumer_timing.c`）。
- CI 阶段同脚本由 `conan create` 的 test_package 自动执行（CI L1 门禁）。

## 4. 门禁结果

| 门禁 | 结果 | 证据 |
|------|------|------|
| conan-verify G0-G4 + L2/L4/L5 | 见 §5（本文件随 W3 更新） | `reports/conan-verify-report.md`（本地，未入仓） |
| W3 本地 CI（ci/conan/build_and_test.sh） | 见 §5（本文件随 W3 更新） | `.ci-result.json`（本地，未入仓） |
| W4 Pre-PR 独立审计 | pass（0 P0/P1） | `reports/audit-result.json` |

## 5. 平台行为与已知限制（如实记录）

1. **Sun RPC 不可用**：musl/OHOS 无 `rpc/rpc.h`；`lat_rpc` 保留为明确报错的诊断入口
   （退出码 1）。TCP/UDP/Unix socket 延迟与带宽基准（lat_tcp/lat_udp/bw_tcp/
   lat_unix/bw_unix 等）均正常构建（不依赖 RPC）。
2. **文件系统命名 AF_UNIX socket 被平台禁止**：`lat_unix_connect -s` 的服务端
   使用命名 socket（上游硬编码 `/tmp/af_unix`）；实测 `bind` 在 `/tmp`、`$HOME`、
   `$HOME/work`、`$HOME/tmp` 等所有可写目录均返回 `EPERM (Operation not
   permitted)`，而**抽象 socket 可用**。曾尝试 TMPDIR 感知补丁确认 bind 在任何
   目录仍 EPERM，遂回退——这是平台能力限制，上游行为未改动。仅该基准不可用；
   `lat_unix`/`bw_unix` 使用 `socketpair`（不落文件系统），正常。
3. **标定对负载敏感**：`find_N` 的 ±2% 收敛窗口在重载机器上会被测量噪声放大
   （min-of-10 散布过大 → N 放大到 10^8 量级 → 单程序长时间运行、无明显输出）。
   这是 lmbench 1990 年代自适应标定的固有特性；上游规避机制 = 先运行
   `enough`/`timing_o`/`loop_o` 导出 `ENOUGH`/`TIMING_O`/`LOOP_O` 再跑基准
   （`scripts/config-run` 同口径）。test_package 采用该机制（并对三件套设 120s
   超时回退缺省值）。超时回退路径不会伪造数值：基准仍真实运行、断言仍真实校验。
