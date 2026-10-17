/*
 * pthread_stubs.c — link-time definitions for pthread entry points that the
 * OHOS bionic libc does not implement (E085 / E051).
 *
 * Evidence: "llvm-nm --undefined-only libfuse.a" lists exactly two undefined
 * pthread symbols that libc does not provide:
 *     pthread_cancel          (referenced by fuse_loop_mt.c and fuse.c)
 *     pthread_setcancelstate  (referenced by fuse_loop_mt.c)
 * The rest of the pthread surface (create, join, mutex, cond, key, sigmask)
 * is provided by OHOS libc.
 *
 * These are ENOSYS-semantics definitions, not empty shells: each reports
 * failure and sets errno, so a caller that actually needs cancellation
 * observes an error instead of silently believing it was cancelled. The
 * offline consumer test never drives the multithreaded loop, so they are not
 * invoked; they exist so a static link against libfuse.a can complete.
 */
#include <errno.h>
#include <pthread.h>

int pthread_cancel(pthread_t thread)
{
    (void)thread;
    errno = ENOSYS;
    return -1;
}

int pthread_setcancelstate(int state, int *oldstate)
{
    if (oldstate != NULL)
        *oldstate = PTHREAD_CANCEL_ENABLE;
    (void)state;
    errno = ENOSYS;
    return -1;
}
