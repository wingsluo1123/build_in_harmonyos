// Consumer test for the wasi-libc sysroot package.
// Compiled to wasm32-wasip1 against the packaged sysroot, then executed
// under a WASI-capable runtime (Node's built-in WASI via wasi-run.mjs).
//
// Expected stdout: each stage prints "OK <name>"; final line "CONSUMER_PASS".
// Exit code 0 on success; non-zero on any failure.
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <time.h>

static int failures = 0;

static void check(const char *name, int cond) {
    if (cond) {
        printf("OK %s\n", name);
    } else {
        printf("FAIL %s (errno=%d %s)\n", name, errno, strerror(errno));
        failures++;
    }
}

static int cmp_int(const void *a, const void *b) {
    return *(const int *)a - *(const int *)b;
}

int main(void) {
    // stdio + string
    char buf[128];
    int n = snprintf(buf, sizeof buf, "%s-%d-%.3f", "wasi", 42, 0.5);
    check("snprintf", n == 13 && strcmp(buf, "wasi-42-0.500") == 0);
    check("strlen", strlen("harmony") == 7);
    check("strstr", strstr("openharmony", "harmony") != NULL);

    // malloc / free
    int *v = malloc(16 * sizeof(int));
    check("malloc", v != NULL);
    if (!v) {
        printf("CONSUMER_FAIL %d\n", failures);
        return 1;
    }
    for (int i = 0; i < 16; i++) v[i] = 15 - i;
    qsort(v, 16, sizeof(int), cmp_int);
    int sorted = 1;
    for (int i = 0; i < 16; i++) if (v[i] != i) sorted = 0;
    check("qsort", sorted);
    free(v);

    // file I/O against the preopen fixture dir (mounted as /)
    const char *path = "/consumer-test.txt";
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0666);
    check("open-create", fd >= 0);
    if (fd >= 0) {
        check("write", write(fd, "hello wasi-libc", 15) == 15);
        check("close", close(fd) == 0);
    }
    fd = open(path, O_RDONLY);
    check("open-read", fd >= 0);
    if (fd >= 0) {
        char rb[32] = {0};
        ssize_t r = read(fd, rb, sizeof rb);
        check("read", r == 15 && memcmp(rb, "hello wasi-libc", 15) == 0);
        check("close2", close(fd) == 0);
    }
    struct stat st;
    check("stat", stat(path, &st) == 0 && st.st_size == 15);
    check("unlink", unlink(path) == 0);

    // time
    time_t t = time(NULL);
    check("time", t > 0);
    struct tm tmv;
    check("gmtime_r", gmtime_r(&t, &tmv) != NULL && tmv.tm_year + 1900 >= 2026);
    char tbuf[32];
    struct tm tm2 = tmv;
    check("strftime", strftime(tbuf, sizeof tbuf, "%Y", &tm2) > 0);

    // environment (passed via the runner)
    check("getenv", getenv("WASI_CONSUMER_ENV") != NULL &&
                    strcmp(getenv("WASI_CONSUMER_ENV"), "ohos") == 0);

    if (failures == 0) {
        printf("CONSUMER_PASS\n");
        return 0;
    }
    printf("CONSUMER_FAIL %d\n", failures);
    return 1;
}
