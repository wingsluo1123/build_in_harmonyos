/*
 * Port of upstream tests/test_invalid_term/test.php to native C.
 *
 * Upstream: putenv("TERM=invalid-term"); tb_init(); tb_shutdown(); then
 * writes "no_segfault" to /dev/tty and screencaps. The point is that an
 * unknown TERM must not crash termbox2.
 *
 * Native: set TERM to an invalid value, init termbox2 on a PTY and shut it
 * down; the test passes as long as no crash/segfault occurs.
 */
#include <stdio.h>
#include <stdlib.h>

#include "tb_test_os.h"

int main(void)
{
    int master = -1, slave = -1;
    int init = 0;
    int rv;

    if (tb_os_open_pty(&master, &slave, 80, 24) != 0) {
        CHECK(0, "open PTY");
        tb_os_report("test_invalid_term");
        return 1;
    }

    CHECK(setenv("TERM", "invalid-term", 1) == 0, "set TERM=invalid-term");
    /* upstream tb_init() with an unknown TERM must not crash */
    rv = tb_os_init_fd(slave, &init);
    (void)rv;
    if (init) {
        tb_shutdown();
        CHECK(tb_width() < 0, "after shutdown termbox is not initialized");
    }

    printf("no_segfault\n");

    tb_os_close(master, slave);
    tb_os_report("test_invalid_term");
    return g_fails != 0 ? 1 : 0;
}
