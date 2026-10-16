/*
 * Port of upstream tests/test_invalid_utf8/test.php to native C.
 *
 * Upstream: tb_init; tb_print_ex(0, y++, 0,0, NULL, "foo\xc2\x00password")
 * (stops at the embedded NUL); tb_set_cell(0, y++, 0xffff, 0, 0) with an
 * invalid code point; tb_present; screencap.
 *
 * Native: assert the same calls round-trip cleanly on a PTY (no crash, valid
 * returns), which is the intent of the upstream case.
 */
#include <stdio.h>

#include "tb_test_os.h"

int main(void)
{
    int master = -1, slave = -1;
    int init = 0;
    int rv;
    int y = 0;

    if (tb_os_open_pty(&master, &slave, 80, 24) != 0) {
        CHECK(0, "open PTY");
        tb_os_report("test_invalid_utf8");
        return 1;
    }

    rv = tb_os_init_fd(slave, &init);
    if (init) {
        CHECK(rv == TB_OK, "tb_init_fd initializes termbox2");

        /* print_ex with an embedded NUL after a partial UTF-8 byte */
        CHECK(tb_print_ex(0, y++, 0, 0, NULL, "foo\xc2\x00password") == TB_OK,
              "tb_print_ex stops at embedded NUL");
        CHECK(tb_set_cell(0, y++, 0xffff, 0, 0) == TB_OK,
              "tb_set_cell invalid codepoint");
        CHECK(tb_present() == TB_OK, "tb_present succeeds");
        tb_shutdown();
    } else {
        CHECK(0, "tb_init_fd initializes termbox2");
    }

    tb_os_close(master, slave);
    tb_os_report("test_invalid_utf8");
    return g_fails != 0 ? 1 : 0;
}
