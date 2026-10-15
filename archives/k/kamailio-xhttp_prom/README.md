# kamailio-xhttp_prom

kamailio 的 Prometheus 指标导出模块，经 xhttp 暴露 `/metrics` 端点。

## Homepage
https://www.kamailio.org/

## License
GPL-2.0-or-later

## Build System
kamailio 经典 Makefile 体系（`make cfg` + `make modules`，非 autotools / cmake）。

## Dependencies
- 构建期：无（源码来自 kamailio 官方 6.0.6 源码包；OHOS SDK clang 15）
- 运行期：kamailio 6.0.6 主程序（宿主）+ OHOS libc（musl）。模块自带 Prometheus
  指标实现（`prom.c` / `prom_metric.c`），**无 libprom 等外部依赖包**。

## OHOS Adaptation
- kamailio 模块源码普遍包含 core 头（`sr_module.h` → `resolve.h` / `sched_yield.h` 等），
  平台宏缺失时直接 `#error`；而 `Makefile.defs` 只识别 linux / solaris / freebsd / darwin
  分支，`OS=harmonyos` 不注入任何 `HAVE_*` 宏。解法：`make ... extra_defs='...'` 注入
  linux 分支等价宏集（`-D_GNU_SOURCE -DHAVE_GETHOSTBYNAME2 -DHAVE_SCHED_YIELD
  -DHAVE_MSG_NOSIGNAL -DHAVE_MSGHDR_MSG_CONTROL -DHAVE_ALLOCA_H -DHAVE_TIMEGM
  -DHAVE_SCHED_SETSCHEDULER -DHAVE_IP_MREQN`），**不改动任何源文件（0 补丁）**。
- 注入宏逐符号在 HarmonyOS（musl）上实证：`gethostbyname2` / `sched_yield` /
  `sched_setscheduler` / `timegm` / `gettimeofday` / `getaddrinfo` 全部由
  `/lib/ld-musl-aarch64.so.1` 导出（`dladdr` 确认）。
- `HAVE_UNION_SEMUN` **不注入**：musl 的 `sys/sem.h` 无 `union semun`（core `lock_ops.h`
  自带条件定义）。
- 模块以 `-Wl,-z,now`（BIND_NOW）构建，`dlopen` 期完成全部重定位 → 消费者测试以
  "能否加载" 作为 ABI/符号闭包完整性判据。
- 模块未定义符号仅两类（kamailio 核心符号 + OHOS libc 符号，无第三类），故适配后
  无需任何额外依赖包即可在平台上加载。

## Verification
- `conan create`（aarch64-linux-ohos，clang 15）从干净源码构建通过（G1/G2/G3/G4 门禁）。
- L1 test_package：消费者进程真实 `dlopen` + 导出表解析（17 项）+ 产物/平台核对（16 项）
  = **33/33 断言通过**。
- 测试设计说明见版本目录 `test_package/`，详细报告见 `<version>/reports/test-report.md`
  （AI 元数据，不入库）。

## Versions
- 6.0.6 — built 2026-09-27（消费者用例 33/33；0 补丁；无外部依赖）
