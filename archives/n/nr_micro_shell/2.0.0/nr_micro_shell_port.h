/*
 * nr_micro_shell_port.h — 默认适配层（putchar 版）
 *
 * 上游设计：nr_micro_shell_port.h 由用户提供。本文件是随包发布的默认
 * 移植层，满足 OHOS/Linux PC 下开箱即用（shell_putc -> putchar、
 * shell_get_ts_ns -> clock_gettime）。消费者可通过把自定义 port 头放在
 * 更靠前的 include 路径来覆盖（上游支持的用法）。
 *
 * 默认启用命令：help / clear / hex2dec / time（均无内存映射等平台需求）。
 * rd/wr 需要目标内存访问权限，默认不启用；NR_SHELL_SHOW_LOGO /
 * NR_SHELL_AUTO_COMPLETE_SUPPORT / NR_SHELL_HISTORY_CMD_SUPPORT 默认开启。
 */

#ifndef __NR_MICRO_SHELL_PORT_H__
#define __NR_MICRO_SHELL_PORT_H__

/* OHOS/musl 工具链下 clock_gettime/CLOCK_MONOTONIC 需 POSIX 特性宏，
   必须在任何系统头之前定义 */
#if defined(__OHOS__) || defined(__linux__)
#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif
#endif

#ifdef __cplusplus
extern "C" {
#endif

#include <stdio.h>
#include <stdint.h>
#include <time.h>

/* Required configuration macros */
#ifndef shell_putc
#define shell_putc(x) putchar((x))
#endif

/* Optional configuration macros */
#ifndef NR_SHELL_MAX_LINE_SZ
#define NR_SHELL_MAX_LINE_SZ 80 /* Maximum command line length */
#endif
#ifndef NR_SHELL_PROMPT
#define NR_SHELL_PROMPT "nr@dev" /* Command prompt string */
#endif
#ifndef NR_SHELL_MAX_PARAM_NUM
#define NR_SHELL_MAX_PARAM_NUM 16 /* Maximum number of parameters per command */
#endif

#define NR_SHELL_CMD_HEX2DEC  /* Enable hexadecimal to decimal conversion */
#define NR_SHELL_CMD_TIME     /* Enable time cmd (needs shell_get_ts_ns) */

#define NR_SHELL_SHOW_LOGO    /* Enable shell logo display */

#define NR_SHELL_AUTO_COMPLETE_SUPPORT /* Enable command auto-completion */
#define NR_SHELL_HISTORY_CMD_SUPPORT   /* Enable command history */
#ifndef NR_SHELL_HISTORY_CMD_NUM
#define NR_SHELL_HISTORY_CMD_NUM 5  /* Number of commands kept in history */
#endif
#ifndef NR_SHELL_HISTORY_CMD_SZ
#define NR_SHELL_HISTORY_CMD_SZ 64  /* Max size of each history command */
#endif

static inline uint64_t nr_micro_shell_default_get_ts_ns(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}
#ifndef shell_get_ts_ns
#define shell_get_ts_ns() nr_micro_shell_default_get_ts_ns()
#endif

#ifdef __cplusplus
}
#endif
#endif /* __NR_MICRO_SHELL_PORT_H__ */