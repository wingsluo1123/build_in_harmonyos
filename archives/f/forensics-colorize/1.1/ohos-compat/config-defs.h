/*
 * config-defs.h — forensics-colorize 1.1 (upstream jessek/colorize) / OpenHarmony
 *
 * 上游是 autotools 工程：configure.ac 生成 config.h，Makefile.am 的
 * ``AM_CPPFLAGS = -I@top_srcdir@`` 把它放进 include 路径，main.h 用
 * ``#ifdef HAVE_CONFIG_H`` 决定是否 include。本配方不跑 autoconf
 * （autoconf/automake 属构建机工具，CI worker 与本机不保证齐备），
 * 改为用 ``-include ohos-compat/config-defs.h`` 强制注入 —— 位置等价于 config.h，
 * 且先于上游 src/main.h 展开（include 顺序：config-defs.h → main.h → config-shim.h）。
 *
 * 本文件只放 configure 会探测出来的宏，不含任何代码。
 * 源码零修改（上游测试用例 / 源码修改 = 否）。
 */

#ifndef FORENSICS_COLORIZE_OHOS_CONFIG_DEFS_H
#define FORENSICS_COLORIZE_OHOS_CONFIG_DEFS_H

/* ---- 相当于 configure 里 AC_CHECK_HEADERS / AC_FUNC_FSEEKO 的结果 ---- */
#define HAVE_INTTYPES_H 1   /* configure.ac 缺它会直接 AC_MSG_ERROR */
#define HAVE_LIBGEN_H 1     /* OHOS sysroot 有 libgen.h：basename() */
/* HAVE_FSEEKO 必须**定义**：
 *   · 上游 main.h 在未定义时会做
 *         #define fseeko  _fseeki64
 *         #define ftello  _ftelli64
 *     这是 Windows (MSVC) 的 64 位替代，OHOS 上不存在 -> 隐式声明 + 链接失败；
 *   · 定义 HAVE_FSEEKO 才会走 musl/bionic 的 fseeko/ftello —— 这一支才正确。
 * configure.ac 的 AC_FUNC_FSEEKO 只在 libc 没有 fseeko 时才**不**定义它，
 * OHOS libc 有 fseeko，故这里定义与 configure 结论一致。 */
#define HAVE_FSEEKO 1

/* HAVE_CONFIG_H 刻意不定义：本文件就是它的替代品。 */

/* ---- 版本号：上游 automake 按 AC_INIT([colorize],[1.1]) 注入 -DVERSION ----
 * 不用命令行 ``-DVERSION=\"1.1\"``：经过 PowerShell → ssh → /bin/sh 多层引号
 * 传递后实测被 sh 拆开，源码里报 "use of undeclared identifier 'VERSION'"。 */
#define VERSION "1.1"

#endif /* FORENSICS_COLORIZE_OHOS_CONFIG_DEFS_H */
