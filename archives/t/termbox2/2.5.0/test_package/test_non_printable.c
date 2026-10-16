/*
 * Port of upstream tests/test_non_printable/test.php to native C.
 *
 * Upstream: tb_init; for each of NULL/control/backspace/tab/newline/0x1f/0x7f,
 * tb_printf the hex and tb_set_cell it; tb_present; screencap. Verifies
 * non-printable code points are handled without error.
 *
 * Native: assert each tb_set_cell round-trips TB_OK on a PTY.
 */
#include <stdio.h>

#include "tb_test_os.h"

int main(void)
{
    int master = -1, slave = -1;
    int init = 0;
    int rv;
    static const uint32_t cps[] = {
        0x00, 0x01, 0x08, 0x09, 0x0a, 0x1f, 0x7f,
    };
    int y = 0;
    size_t i;

    if (tb_os_open_pty(&master, &slave, 80, 24) != 0) {
        CHECK(0, "open PTY");
        tb_os_report("test_non_printable");
        return 1;
    }

    rv = tb_os_init_fd(slave, &init);
    if (init) {
        CHECK(rv == TB_OK, "tb_init_fd initializes termbox2");
        for (i = 0; i < sizeof(cps) / sizeof(cps[0]); ++i) {
            CHECK(tb_printf(0, y, 0, 0, "0x%02x ", cps[i]) >= 0,
                  "tb_printf hex of non-printable");
            CHECK(tb_set_cell(5, y, cps[i], 0, 0) == TB_OK,
                  "tb_set_cell non-printable");
            y += 1;
        }
        CHECK(tb_present() == TB_OK, "tb_present succeeds");
        tb_shutdown();
    } else {
        CHECK(0, "tb_init_fd initializes termbox2");
    }

    tb_os_close(master, slave);
    tb_os_report("test_non_printable");
    return g_fails != 0 ? 1 : 0;
}
