/*
 * glibc-shim.c — Minimal stub implementations of glibc-specific symbols
 * missing from musl libc on HarmonyOS.
 *
 * These stubs allow the glibc-dynamic pre-compiled git-xet binary to run
 * on musl-based HarmonyOS by providing weak/no-op implementations of
 * functions that glibc provides but musl does not.
 *
 * Built as a shared library: libglibc-shim.so
 *   clang -shared -fPIC -o libglibc-shim.so glibc-shim.c -lpthread
 */

#include <string.h>
#include <pthread.h>
#include <unistd.h>
#include <sys/types.h>

/* glibc's __res_state returns a per-thread resolver state structure.
 * musl's resolver is simpler; we provide a static dummy. */
struct __res_state_shim {
    int dummy;
};

static struct __res_state_shim _res_shim;

struct __res_state_shim *__res_state(void) {
    return &_res_shim;
}

/* __res_init: glibc resolver initialization. musl doesn't need it. */
int __res_init(void) {
    return 0;
}

/* gnu_get_libc_version: returns glibc version string. */
const char *gnu_get_libc_version(void) {
    return "2.31";
}

/* pthread_mutexattr_setrobust: glibc extension for robust mutexes.
 * musl doesn't support robust mutexes; we provide a no-op. */
int pthread_mutexattr_setrobust(pthread_mutexattr_t *attr, int robustness) {
    /* PTHREAD_MUTEX_STALLED = 0, PTHREAD_MUTEX_ROBUST = 1 */
    return 0;
}

/* pthread_mutex_consistent: mark a robust mutex as consistent.
 * No-op in musl since robust mutexes aren't supported. */
int pthread_mutex_consistent(pthread_mutex_t *mutex) {
    return 0;
}
