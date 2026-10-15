# DRAFT: lwdtc-1.0.0 — Windows 专用 localtime_s 默认配置在 OHOS musl 下未声明，注入用户 opts 改用 localtime_r

> 来源：lwdtc 1.0.0 适配（pc2-9, task lwdtc-1.0.0-r01-bootstrap-and-adapt-pc2-9-20260921T150347Z）
> 状态：pending-editor-review（拟提升编号 E###，最终由主编确认）

## 错误特征

OHOS (musl libc) 下编译 lwdtc 库本体（`lwdtc.c`）报：

- `call to undeclared function 'localtime_s'`（`-Wimplicit-function-declaration`，`-Werror` 下直接 error；错误定位在宏展开 `LWDTC_CFG_GET_LOCALTIME`）
- 缺省 `lwdtc_opt.h` 默认宏：`#define LWDTC_CFG_GET_LOCALTIME(_sp_, _tp_) (void)localtime_s((_sp_), (_tp_))`
- 若 `lwdtc_opts.h` 用户配置缺失，`lwdtc_opt.h` 还会报 `'lwdtc_opts.h' file not found`

## 根因

lwdtc（MaJerle 系列库通用模式）把平台相关行为放进**用户可覆盖的 opts 头**：`lwdtc_opt.h` 用 `#ifndef` 守卫提供默认实现，其中 `LWDTC_CFG_GET_LOCALTIME` 默认调用 `localtime_s`。`localtime_s` 是 Windows/MSVC 风格 API（参数序 `struct tm*, const time_t*`），OHOS musl libc 不提供该符号（只提供 POSIX `localtime_r`，参数序相反 `const time_t*, struct tm*`）。因此任何未覆盖该宏的消费者在 OHOS 上编译即失败；链接期同样缺符号。这是“上游默认值绑定 Windows API、OHOS 无对应符号”的通用模式，不是 lwdtc 单一缺陷。

## 方案

不修改上游源码，用 lwdtc 官方提供的用户配置机制注入 OHOS 适配头：

1. 配方 `generate()` 生成 `lwdtc_opts.h`（内容见下），放入构建树私有 gen 目录并加入 include 路径（在 `lwdtc/src/include` 之前）。
2. 宏内做**参数重排**：`localtime_r((_const_time_t_ptr_), (_struct_tm_ptr_))`。
3. 通过最小 CMake wrapper 将 `lwdtc.c` 编译为静态库；`lwdtc_opts.h` 随包安装到 `include/`，消费者开箱即用。

```c
#ifndef LWDTC_CFG_GET_LOCALTIME
#define LWDTC_CFG_GET_LOCALTIME(_struct_tm_ptr_, _const_time_t_ptr_) \
    (void)localtime_r((_const_time_t_ptr_), (_struct_tm_ptr_))
#endif
```

## 验证

- OHOS clang `-Wall -Wextra -Werror` 编译 `lwdtc.c` 通过（注入 opts 后零警告）
- 消费者 smoke：`lwdtc_cron_parse("30 * * * * * *")` + `lwdtc_cron_is_valid_for_time` + `lwdtc_cron_next` 全 PASS
- conan create（ohos-aarch64 profile）G0-G4 全过；test_package 真实 API 调用 PASS；W3 本地 CI 模拟通过
- 不修改任何上游源文件（0 patch）

## 适用边界

- **适用**：所有 MaJerle 系 C 库（lwdtc/lwbtn/lwmem/lwow 等）及其他“用户 opts 头覆盖平台默认值”模式的库，在 OHOS/musl 上遇 Windows 专用 API 默认值时
- **适用**：任何默认依赖 `localtime_s`（或其它 Windows-only 符号）而 OHOS 提供 POSIX 替代（`localtime_r`）的库
- **不适用**：运行期才依赖系统时区服务的场景（那是 R40 深度适配/时区契约边界，参见 E315 R 时区条目）
- **不适用**：非 opts 机制的库（需走 patch 或 `-D` 编译定义注入，遵循 R8 平台宏规范）

## 反例/限制

- 反例：直接 `#define LWDTC_CFG_GET_LOCALTIME` 不重排参数直接调用 `localtime_r((_sp_), (_tp_))` —— 参数序错误，运行时写入非法指针。
- 反例：在 patches/ 补丁里给上游源码硬塞 `#ifdef __OHOS__` 分支 —— 违反 R8（patches 默认禁平台宏），本方案用用户配置头规避。
- 限制：注入头须放在上游 include 目录**之前**（`#include "lwdtc_opts.h"` 的引号查找先找同目录，故 CMake wrapper 中把 gen 目录显式放最前）。
