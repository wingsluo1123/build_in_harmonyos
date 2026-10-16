/*
 * Port of upstream tests/test_fd_leak/test.php to native C.
 *
 * Upstream: create a memfd, count /proc/self/fd entries, call tb_init_file()
 * on "/proc/self/fd/<memfd>" (a non-tty), tb_shutdown(), recount and report
 * num_fds_leaked. The upstream expectation (expected.ansi) is 0.
 *
 * Native: identical logic; assert that tb_init_file()/tb_shutdown() on a
 * non-tty does not leak the descriptor it opened.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#include "tb_test_os.h"

static int count_fds(void)
{
    DIR *d = opendir("/proc/self/fd");
    struct dirent *e;
    int n = 0;

    if (d == NULL)
        return -1;
    while ((e = readdir(d)) != NULL) {
        if (e->d_name[0] != '.')
            ++n;
    }
    closedir(d);
    return n;
}

int main(void)
{
    int memfd;
    int before, after, leaked;
    char path[64];

    memfd = memfd_create("rw", 0);
    if (memfd < 0) {
        CHECK(0, "memfd_create");
        tb_os_report("test_fd_leak");
        return 1;
    }

    before = count_fds();
    CHECK(before > 0, "/proc/self/fd is readable");

    snprintf(path, sizeof(path), "/proc/self/fd/%d", memfd);
    tb_init_file(path);
    tb_shutdown();

    after = count_fds();
    leaked = after - before;

    close(memfd);

    CHECK(leaked == 0, "tb_init_file on a non-tty does not leak an fd");

    tb_os_report("test_fd_leak");
    return g_fails != 0 ? 1 : 0;
}
