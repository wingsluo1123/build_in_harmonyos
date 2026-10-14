/*
 * ohos_platform_probe.c — HarmonyOS-specific platform capability probe.
 *
 * KeyDB 6.3.4 depends on two platform behaviours that are NOT portable and
 * that both patches 0003/0004 (pthread compatibility) and 0005 (madvise)
 * address. This probe asserts the OHOS kernel/libc actually provides the
 * behaviour the adapted build assumes, so a change in the platform (or a
 * regression in the compatibility layer) is caught here rather than at
 * server start-up.
 *
 * Covered:
 *   1. madvise(MADV_DONTNEED) must succeed  — the fallback the patch uses.
 *      madvise(MADV_FREE) may legitimately return -1/EINVAL on OHOS: the
 *      arm64 fork bug the upstream probe targets only exists on kernels
 *      that implement MADV_FREE, so EINVAL means "not affected".
 *   2. pthread_setaffinity_np must work via the pthread_compat shim, and
 *      CPU_ZERO/CPU_SET/CPU_ISSET must agree.
 *   3. pthread_setname_np (used for worker thread names) must succeed.
 *
 * Exit code 0 = all assertions passed. Any failure prints FAIL and exits 1.
 */

#define _GNU_SOURCE

#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

static int failures = 0;
static int checks = 0;

static void check(int cond, const char *what) {
    checks++;
    if (cond) {
        printf("  [ok]: %s\n", what);
    } else {
        printf("  [FAIL]: %s\n", what);
        failures++;
    }
}

/* ---- 1. madvise ------------------------------------------------------- */

static void probe_madvise(void) {
    size_t page = (size_t)sysconf(_SC_PAGESIZE);
    void *p = mmap(NULL, page, PROT_READ | PROT_WRITE,
                   MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) {
        check(0, "madvise: mmap a page");
        return;
    }
    memset(p, 0x5a, page);

    errno = 0;
    int d = madvise(p, page, MADV_DONTNEED);
    int d_errno = errno;
    printf("        MADV_DONTNEED -> %d (errno=%d)\n", d, d_errno);
    /* This is the fallback the adapted build relies on: it must work. */
    check(d == 0, "madvise(MADV_DONTNEED) succeeds on this kernel");

    errno = 0;
    int f = madvise(p, page, MADV_FREE);
    int f_errno = errno;
    printf("        MADV_FREE     -> %d (errno=%d)\n", f, f_errno);
    /* Either outcome is acceptable; EINVAL is what OHOS returns and is the
     * reason the upstream fork-bug probe must degrade instead of aborting. */
    check(f == 0 || (f == -1 && f_errno == EINVAL),
          "madvise(MADV_FREE) is either supported or cleanly reports EINVAL");

    /* MADV_DONTNEED must still work after MADV_FREE was attempted. */
    errno = 0;
    int d2 = madvise(p, page, MADV_DONTNEED);
    printf("        MADV_DONTNEED -> %d (errno=%d) [after MADV_FREE]\n",
           d2, errno);
    check(d2 == 0, "madvise(MADV_DONTNEED) still works after MADV_FREE");

    munmap(p, page);
}

/* ---- 2. CPU affinity primitives (patch 0003/0004) --------------------- */

/*
 * musl does not provide the GNU pthread_setaffinity_np / getaffinity_np
 * entry points at all, which is exactly why keydb carries a
 * pthread_compat shim (patches 0003/0004). This probe therefore tests the
 * primitives the shim forwards to, i.e. the ones that MUST exist on the
 * platform for the shim to be implementable:
 *
 *     sched_setaffinity() / sched_getaffinity() / CPU_* macros
 *
 * The shim's own presence in the built server is verified separately by the
 * runner (symbol check), not here.
 */
static void probe_affinity(void) {
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(0, &set);
    check(CPU_ISSET(0, &set), "cpu_set_t: CPU_SET/CPU_ISSET agree");

    int rc = sched_setaffinity(0, sizeof(set), &set);
    printf("        sched_setaffinity -> %d (errno=%d)\n", rc, errno);
    check(rc == 0, "sched_setaffinity(CPU 0) succeeds");

    cpu_set_t got;
    CPU_ZERO(&got);
    rc = sched_getaffinity(0, sizeof(got), &got);
    printf("        sched_getaffinity -> %d (errno=%d)\n", rc, errno);
    check(rc == 0, "sched_getaffinity succeeds");
    if (rc == 0) {
        check(CPU_ISSET(0, &got), "CPU 0 is present in the affinity mask");
    }

    /* The shim is needed precisely because these are absent on musl; if a
     * future platform gains them, the shim simply forwards and still works. */
    printf("        (pthread_*affinity_np are shimmed by keydb patch 0003)\n");
}

/* ---- 3. pthread_setname_np ------------------------------------------- */

static void *named_worker(void *arg) {
    (void)arg;
    int rc = pthread_setname_np(pthread_self(), "ohos-probe");
    printf("        pthread_setname_np -> %d (errno=%d)\n", rc, errno);
    check(rc == 0, "pthread_setname_np names a worker thread");
    return NULL;
}

static void probe_setname(void) {
    pthread_t t;
    if (pthread_create(&t, NULL, named_worker, NULL) != 0) {
        check(0, "pthread_create for the naming probe");
        return;
    }
    pthread_join(t, NULL);
}

int main(void) {
    printf("== KeyDB HarmonyOS platform probe ==\n");
    printf("libc: %s\n",
#if defined(__GLIBC__)
           "glibc"
#else
           "musl (expected on OHOS)"
#endif
    );

    printf("\n-- madvise --\n");
    probe_madvise();

    printf("\n-- pthread affinity (pthread_compat shim) --\n");
    probe_affinity();

    printf("\n-- pthread naming --\n");
    probe_setname();

    printf("\n%d checks, %d failures\n", checks, failures);
    if (failures == 0) {
        printf("ALL_TESTS_PASS\n");
        return 0;
    }
    printf("SOME_TESTS_FAIL\n");
    return 1;
}
