# DRAFT: lwdtc 1.0.0 R02 — 上游测试入口的 windows.h 宿主头 POSIX 单一路径兼容复跑

> 来源：lwdtc 1.0.0 R02 Review 修复轮（task lwdtc-1.0.0-r02-upstream-test-vector-and-example-execution-pc2-9-20260927T050718Z）
> 状态：pending-editor-review（拟提升编号 E###，最终由主编确认）

## 错误特征

赛事 Review 规则 4「验证结果」FAIL：上游交付态存在可执行测试入口
（`dev/main.c` 表驱动测试向量 harness + `examples/` 4 个入口），但 R01 将其
全部判为 `windows.h 专用 → 不可运行`，声明上游用例 0/4，构成"少报
（实测 N > 声明 N）"。

直接表象：`dev/main.c` 与 `examples/*.c` 都 `#include <windows.h>`，OHOS
无此头 → 编译期 `fatal error: 'windows.h' file not found`。若不作审计就把
"上游示例用 windows.h"当作不可运行/外部阻塞，就会漏报全部上游测试入口。

## 根因

1. `windows.h` 只被**宿主/示例代码**（`dev/`、`examples/`）使用，提供的是
   `Sleep(ms)` 与 `GetTickCount64()` 计时原语；**库发布物**（`lwdtc/src/**`
   与安装的头/库）零依赖它。把"示例用了 windows.h"等价于"库不可运行"是
   归因错误。
2. 顶层 `CMakeLists.txt` 的 `dev` 可执行目标把 `dev/main.c` + 4 个 examples
   聚合为一个程序（`target_sources(... dev/main.c examples/*.c)`），示例文件
   本身没有 `main()`（定义 `cron_basic()`/`cron_multi()`/`cron_dt_range()`/
   `cron_calc_range()` 入口函数）——独立编译会报 `undefined symbol: main`。
3. 部分入口是无限循环（`while (1)` + `Sleep(100)`），无退出条件、无测试数/
   时长参数，不可能自然 `exit 0`。
4. `dev/main.c` 用 `localtime()` 格式化输出并与硬编码期望串比较，期望串按
   作者本地时区（UTC+2）撰写——在默认时区（如 CST）下所有断言偏移失败，
   易被误判为"库实现缺陷"（实测四个时区采样下仅 UTC+2 全过）。

## 方案

不修改任何上游逻辑，按"宿主兼容 + 受控完成"两条路径真实执行全部上游入口：

1. **宿主 POSIX 兼容头**（单一路径，无平台宏）：提供 `Sleep(ms)`→
   `nanosleep`（EINTR 重试）、`GetTickCount64()`→`clock_gettime(CLOCK_MONOTONIC)`，
   命名为 `windows.h` 放入独立 include 目录注入 `-I`（不进入交付物或仅随
   reports 交付源码）。禁止 `#ifdef __OHOS__` 平台宏。
2. **入口聚合 runner**：示例文件无 `main()`，用 `-DENTRY=cron_xxx` 单入口
   宏版 runner 提供 main 调用点（一个二进制只引用一个示例符号），避免
   undefined symbol 链接错误。
3. **harness 时区前置**：`dev/main.c` 期望串按 UTC+2 撰写，运行环境设
   `TZ=UTC-2`（POSIX 单一路径环境变量，不改期望值、不裁剪向量）；如实记录
   默认时区失败为 harness 隐式时区前提，非库缺陷。
4. **受控完成**：无限循环入口运行 ≥60s 最小阈值，后台编排器向原始子进程
   发 `SIGINT`（禁 timeout/SIGKILL/改源码/伪造 exit 0），记录原始信号退出
   状态（128+SIGINT=130）与输出类别。
5. **可失败性实证**：worktree 外临时副本篡改期望值，观测真实非零退出与
   `Test failed: …` 输出后恢复交付态（sha256 对照），证明 harness 非恒绿。
6. **占位入口如实分类**：`cron_calc_range.c` 为上游占位（`TODO` + 无条件
   `return 1`，无断言），真实运行→如实记 rc=1，不计"断言通过"、不写成不可
   运行、不自行实现 TODO。

## 验证

- `dev/main.c` + 库源码 OHOS clang 真实编译成功（3 个上游自身警告原样保留）
- harness 真实运行至自然退出：TZ=UTC-2 下 exit 0、`Test failed` 0 次、
  `Total tick: 337`；17 条向量 × 100 轮
- 失败变体（篡改期望串）运行 exit 255 + `Test failed: cron: …`
- 4 个示例入口全部真实编译并受控/如实运行，独立日志 + SHA-256 随 PR 交付
- 每个门禁独立日志（unique_log_paths_required）、log_sha256 均提供
- `上游测试用例统计` 21（17 向量 + 4 示例）；适配后实际执行 22（上游 21 +
  鸿蒙特有 1）；实测 N ≤ 声明 N，少报核验成立

## 适用边界

- **适用**：任何上游用 `windows.h` 宿主头（Sleep/GetTickCount64 等计时原语）
  但库发布物不依赖它的 C 库；任何含 `while(1)` 无限示例/测试入口的库；
  任何用 `localtime()` + 硬编码期望串做断言（期望串隐含作者时区）的 harness。
- **不适用**：库运行时自身强依赖 Windows 系统的场景（那是 R40 深度适配边界）；
  不适用需要真实 Windows API 语义而 POSIX 无等价物的场景。

## 反例/限制

- 反例：把"示例用 windows.h"直接写成 `不可运行`/`外部阻塞`——导致规则 4
  少报 FAIL（本任务根因）。
- 反例：用 `timeout` 包无限入口并把 `124` 当成功；或发 `SIGKILL`；或改源码
  删 `while(1)` 伪造自然退出。
- 反例：把 `return 1` 占位入口写成通过；或自行实现 TODO 算法凑通过。
- 限制：兼容头若含平台条件编译宏会被 CI 拦截（R8/PF5 口径）；注入头须在
  交付态保持与运行态一致（sha256 对照）。