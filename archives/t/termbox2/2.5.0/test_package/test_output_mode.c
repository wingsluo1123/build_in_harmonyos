/*
 * Port of upstream tests/test_output_mode/test.php to native C.
 *
 * Upstream: tb_init; tb_printf a cyan line; tb_present; switch to
 * TB_OUTPUT_GRAYSCALE; tb_printf a gray line; tb_present; screencap. Verifies
 * output mode switching keeps rendering valid.
 *
 * Native: assert the same calls round-trip TB_OK on a PTY.
 */
#include <stdio.h>

#include "tb_test_os.h"

int main(void)
{
    int master = -1, slave = -1;
    int init = 0;
    int rv;
    unsigned int fg = 7;
    int y = 0;

    if (tb_os_open_pty(&master, &slave, 80, 24) != 0) {
        CHECK(0, "open PTY");
        tb_os_report("test_output_mode");
        return 1;
    }

    rv = tb_os_init_fd(slave, &init);
    if (init) {
        CHECK(rv == TB_OK, "tb_init_fd initializes termbox2");

        CHECK(tb_printf(0, y++, fg, 0, "cyan (even after mode switch)") >= 0,
              "tb_printf cyan");
        CHECK(tb_present() == TB_OK, "tb_present first");

        CHECK(tb_set_output_mode(TB_OUTPUT_GRAYSCALE) == TB_OK,
              "switch to GRAYSCALE");
        CHECK(tb_printf(0, y++, fg, 0, "gray") >= 0, "tb_printf gray");
        CHECK(tb_present() == TB_OK, "tb_present second");
        tb_shutdown();
    } else {
        CHECK(0, "tb_init_fd initializes termbox2");
    }

    tb_os_close(master, slave);
    tb_os_report("test_output_mode");
    return g_fails != 0 ? 1 : 0;
}
