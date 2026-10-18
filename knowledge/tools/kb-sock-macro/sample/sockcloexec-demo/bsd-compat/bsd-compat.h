/*
 * KB-SOCK-MACRO 样例库 — 上游 BSD 兼容层形态（未加守卫，故意保留缺陷）
 *
 * 形态来源：sndio 1.10.0 bsd-compat/bsd-compat.h（修复前）
 *   #ifndef HAVE_SOCK_CLOEXEC
 *   #define SOCK_CLOEXEC	0
 *   #endif
 *
 * 老 BSD / 缺 socket 扩展位的系统确实需要兜底；但 OHOS musl 已经提供
 * SOCK_CLOEXEC（02000000）与 SOCK_NONBLOCK（04000），此处兜底把值改成 0，
 * 会覆盖系统真值：
 *   - 编译期：macro redefined（-Werror 下直接失败）
 *   - 运行期：socket() 的 CLOEXEC/NONBLOCK 位静默丢失
 */
#ifndef DEMO_BSD_COMPAT_H
#define DEMO_BSD_COMPAT_H

#ifndef HAVE_SOCK_CLOEXEC
#define SOCK_CLOEXEC 0
#endif

#ifndef HAVE_SOCK_NONBLOCK
#define SOCK_NONBLOCK 0
#endif

#endif /* DEMO_BSD_COMPAT_H */
