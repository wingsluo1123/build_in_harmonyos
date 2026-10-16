/*
 * ohos-compat.h — HarmonyOS (OHOS musl) libc compatibility layer for rdma-core.
 *
 * Force-included into every translation unit by the recipe (see
 * conanfile.py generate(): CMAKE_C_FLAGS/CMAKE_CXX_FLAGS get
 * "-include <this file>"). It closes the gaps between the OHOS libc
 * surface (headers + sysroot import library) and the GNU/BSD symbols
 * rdma-core relies on, without touching upstream sources.
 *
 * Symbol-by-symbol rationale
 * --------------------------
 * 1. POSIX thread cancellation (pthread_cancel / setcancelstate /
 *    setcanceltype / testcancel)
 *      - Not declared by the OHOS <pthread.h> and not exported by the
 *        OHOS sysroot libc.so, so calls fail at compile and link time.
 *      - The runtime libc does export the symbols, but OHOS does not
 *        implement cancellation: pthread_cancel() returns ENOSYS (38).
 *      - Bridging rule used here:
 *          pthread_cancel()      -> forward to the platform. When the
 *                                   platform reports failure the caller
 *                                   takes its documented error path
 *                                   instead of blocking in
 *                                   pthread_join() on a thread that can
 *                                   never be cancelled.
 *          setcancelstate/type   -> report success. Cancellation is never
 *                                   delivered on OHOS, but accepting the
 *                                   request keeps the guarded worker
 *                                   threads (ibacm SA responder,
 *                                   librdmacm examples) running instead
 *                                   of aborting at startup.
 *          testcancel()          -> no-op.
 *      - Thread teardown that genuinely needs to stop a blocked worker
 *        must not rely on cancellation. librdmacm/examples/rping.c is
 *        patched to exit its CQ thread from a reserved signal and join
 *        it (see patches/0001-librdmacm-examples-rping.c.patch).
 *
 * 2. getpass() — GNU extension, absent from OHOS headers and sysroot.
 *    A weak reference forwards to the implementation exported by the
 *    runtime libc when present, otherwise the termios no-echo fallback
 *    below is used.
 *
 * 3. rindex() — historic BSD alias for strrchr(), dropped by OHOS musl.
 *    Alias it to the POSIX equivalent.
 *
 * 4. program_invocation_short_name — glibc-only CRT symbol. OHOS musl
 *    exports the BSD/musl equivalent __progname instead.
 *
 * 5. strdupa() — the OHOS <string.h> only exposes it under _GNU_SOURCE.
 *    rdma-core's own probe (CMakeLists.txt, HAS_CLOEXEC_GNU_SOURCE) adds
 *    _GNU_SOURCE only on the uclibc path, so the recipe passes it
 *    explicitly.
 */
#ifndef RDMA_OHOS_COMPAT_H
#define RDMA_OHOS_COMPAT_H

#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>

/* ---- 1. POSIX thread cancellation ---------------------------------- */

extern int pthread_cancel(pthread_t thread) __attribute__((weak));
extern int pthread_setcancelstate(int state, int *oldstate) __attribute__((weak));
extern int pthread_setcanceltype(int type, int *oldtype) __attribute__((weak));
extern void pthread_testcancel(void) __attribute__((weak));

static inline int rdma_ohos_pthread_cancel(pthread_t thread)
{
	int (*fn)(pthread_t) = pthread_cancel;

	return fn ? fn(thread) : ENOSYS;
}

static inline int rdma_ohos_pthread_setcancelstate(int state, int *oldstate)
{
	(void)state;
	if (oldstate)
		*oldstate = PTHREAD_CANCEL_ENABLE;
	return 0;
}

static inline int rdma_ohos_pthread_setcanceltype(int type, int *oldtype)
{
	(void)type;
	if (oldtype)
		*oldtype = PTHREAD_CANCEL_DEFERRED;
	return 0;
}

static inline void rdma_ohos_pthread_testcancel(void)
{
}

#define pthread_cancel(thread) rdma_ohos_pthread_cancel(thread)
#define pthread_setcancelstate(state, oldstate) \
	rdma_ohos_pthread_setcancelstate(state, oldstate)
#define pthread_setcanceltype(type, oldtype) \
	rdma_ohos_pthread_setcanceltype(type, oldtype)
#define pthread_testcancel() rdma_ohos_pthread_testcancel()

/* ---- 2. getpass() --------------------------------------------------- */

extern char *getpass(const char *prompt) __attribute__((weak));

static inline char *rdma_ohos_getpass(const char *prompt)
{
	static char buf[128];
	struct termios saved, noecho;
	char *(*fn)(const char *) = getpass;
	size_t len;
	int fd = fileno(stdin);
	int have_saved = 0;

	if (fn)
		return fn(prompt);

	if (tcgetattr(fd, &saved) == 0) {
		have_saved = 1;
		noecho = saved;
		noecho.c_lflag &= ~(tcflag_t)ECHO;
		tcsetattr(fd, TCSAFLUSH, &noecho);
	}
	if (prompt) {
		fputs(prompt, stderr);
		fflush(stderr);
	}
	if (fgets(buf, sizeof(buf), stdin) == NULL)
		buf[0] = '\0';
	fputc('\n', stderr);
	if (have_saved)
		tcsetattr(fd, TCSAFLUSH, &saved);

	len = strlen(buf);
	while (len > 0 && (buf[len - 1] == '\n' || buf[len - 1] == '\r'))
		buf[--len] = '\0';
	return buf;
}

#define getpass(prompt) rdma_ohos_getpass(prompt)

/* ---- 3. rindex() ---------------------------------------------------- */

#ifndef rindex
#define rindex strrchr
#endif

/* ---- 4. program_invocation_short_name ------------------------------- */

extern char *__progname;
#define program_invocation_short_name __progname

#endif /* RDMA_OHOS_COMPAT_H */
