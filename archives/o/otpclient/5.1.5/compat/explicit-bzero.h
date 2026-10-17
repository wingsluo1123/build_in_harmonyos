/*
 * explicit-bzero.h — 缺失 libc API 的可移植回退
 *
 * 背景：explicit_bzero() 是 glibc / BSD 扩展，OHOS（musl）未声明该函数，
 * 调用点会被 clang 报 `call to undeclared function 'explicit_bzero'`，
 * 配合上游 -Werror 直接中断编译。
 *
 * 用法：CMakeLists.txt 用 check_c_source_compiles 探测 libc 是否自带
 * explicit_bzero；缺失时以 -include 方式强制包含本头文件，为所有翻译单元
 * 提供静态内联回退实现（不新增导出符号，不改变任何 target 的链接关系）。
 */
#ifndef OTPCLIENT_COMPAT_EXPLICIT_BZERO_H
#define OTPCLIENT_COMPAT_EXPLICIT_BZERO_H

#include <string.h>

#if !defined(HAVE_EXPLICIT_BZERO)

static inline void
explicit_bzero(void *s, size_t n)
{
    memset(s, 0, n);
    /* 阻止编译器把这次 memset 作为无用写入优化掉 */
    __asm__ __volatile__ ("" : : "r" (s) : "memory");
}

#endif /* !HAVE_EXPLICIT_BZERO */

#endif /* OTPCLIENT_COMPAT_EXPLICIT_BZERO_H */
