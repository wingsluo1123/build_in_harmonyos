/*
 * config-shim.h — forensics-colorize 1.1 (upstream jessek/colorize) / OpenHarmony shim
 *
 * 本文件由 ``-include`` 强制注入**每个**编译单元，排在源码末尾 ——
 * 负责 `__progname` 在非 glibc 平台上的唯一定义。
 *
 * 编译命令（见 conanfile.py 的 _flags()）：
 *
 *     clang -I src -D__progname=__fc_progname__        \
 *           -include ohos-compat/config-defs.h         \   # 等价于 autoconf 的 config.h
 *           -include src/main.h                        \   # 1) 先展开上游头
 *           -include ohos-compat/config-shim.h             # 2) 再放定义
 *     helpers.c 额外带 -DFORENSICS_COLORIZE_PROGNAME_TU
 *
 * 上游 main.h 第 43-47 行：
 *
 *     #ifdef __GLIBC__
 *     extern char *__progname;
 *     #else
 *     char *__progname;      <-- 强定义
 *     #endif
 *
 * OHOS 不是 glibc，main.h 在**每个** TU 里都会定义一份 ``__progname``，
 * 实测 ld.lld 报 ``duplicate symbol: __progname``（ui.c / helpers.c /
 * colorize.c 各一份）。``-D__progname=xxx`` 本身解决不了 —— 宏替换按 TU 进行。
 *
 * 解法：
 *   1) ``-D__progname=__fc_progname__`` 把 main.h 那行改名为 ``__fc_progname__``
 *      （形态与上游完全一致：仍是 TU 内的强定义，源码零修改）；
 *      同时改名避免与 libc 内部的同名符号纠缠。
 *   2) 本文件把「非 helpers.c 的 TU」里的定义降级为 **弱定义**，
 *      helpers.c（FORENSICS_COLORIZE_PROGNAME_TU）保留强定义。
 *      链接时强定义优先、弱定义被丢弃 —— 与 glibc 下「libc 定义 + extern 声明」
 *      的符号结果一致（实测 ``llvm-nm`` 只有一个 ``__fc_progname__``）。
 */

#ifndef FORENSICS_COLORIZE_OHOS_CONFIG_SHIM_H
#define FORENSICS_COLORIZE_OHOS_CONFIG_SHIM_H

#if !defined(__GLIBC__) && !defined(__fc_progname_weak__)
#  define __fc_progname_weak__ 1
#  ifndef FORENSICS_COLORIZE_PROGNAME_TU
/* non-helpers TU: weak definition, dropped at link time */
__attribute__((weak)) char *__fc_progname__;
#  else
/* helpers.c: the single strong definition */
char *__fc_progname__;
#  endif
#endif

#endif /* FORENSICS_COLORIZE_OHOS_CONFIG_SHIM_H */
