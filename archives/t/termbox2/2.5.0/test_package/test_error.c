/*
 * Port of upstream tests/test_error/test.php to native C.
 *
 * Upstream: tb_init; attempt tb_set_cell(-1, -1, ...) which is out of bounds,
 * capture the returned error and tb_strerror() text; present; screencap.
 *
 * Native: assert the out-of-bounds call returns the documented error code and
 * that tb_strerror() produces a non-empty human-readable string.
 */
#include <stdio.h>
#include <string.h>

#include "tb_test_os.h"

int main(void)
{
    int master = -1, slave = -1;
    int init = 0;
    int rv;
    int err;

    if (tb_os_open_pty(&master, &slave, 80, 24) != 0) {
        CHECK(0, "open PTY");
        tb_os_report("test_error");
        return 1;
    }

    rv = tb_os_init_fd(slave, &init);
    if (init) {
        CHECK(rv == TB_OK, "tb_init_fd initializes termbox2");

        /* upstream tb_set_cell(-1, -1, 'x', 0, 0) -> error */
        err = tb_set_cell(-1, -1, (uint32_t)'x', 0, 0);
        CHECK(err == TB_ERR_OUT_OF_BOUNDS, "out-of-bounds returns TB_ERR_OUT_OF_BOUNDS");

        {
            const char *msg = tb_strerror(err);
            CHECK(msg != NULL && strlen(msg) > 0, "tb_strerror non-empty");
        }

        CHECK(tb_present() == TB_OK, "tb_present succeeds");
        tb_shutdown();
    } else {
        CHECK(0, "tb_init_fd initializes termbox2");
    }

    tb_os_close(master, slave);
    tb_os_report("test_error");
    return g_fails != 0 ? 1 : 0;
}
