/*
 * Port of upstream tests/test_64bit/test.php to native C.
 *
 * Upstream: skip unless tb_attr_width()==64; then tb_init and tb_printf each
 * of TB_STRIKEOUT / TB_INVISIBLE / TB_UNDERLINE_2 attribute lines; tb_present;
 * screencap.
 *
 * Native: the packaged library is built with TB_LIB_OPTS (TB_OPT_ATTR_W=64), so
 * tb_attr_width() is 64 and the 64-bit-only attribute tests actually run here.
 */
#include <stdio.h>

#include "tb_test_os.h"

int main(void)
{
    int master = -1, slave = -1;
    int init = 0;
    int rv;

    CHECK(tb_attr_width() == 64, "tb_attr_width()==64 (TB_LIB_OPTS)");

    if (tb_os_open_pty(&master, &slave, 80, 24) != 0) {
        CHECK(0, "open PTY");
        tb_os_report("test_64bit");
        return 1;
    }

    rv = tb_os_init_fd(slave, &init);
    if (init) {
        CHECK(rv == TB_OK, "tb_init_fd initializes termbox2");
        CHECK(tb_printf(0, 0, TB_STRIKEOUT, 0, "attr=TB_STRIKEOUT") >= 0,
              "tb_printf strokeout");
        CHECK(tb_printf(0, 1, TB_INVISIBLE, 0, "attr=TB_INVISIBLE") >= 0,
              "tb_printf invisible");
        CHECK(tb_printf(0, 2, TB_UNDERLINE_2, 0, "attr=TB_UNDERLINE_2") >= 0,
              "tb_printf underline_2");
        CHECK(tb_present() == TB_OK, "tb_present succeeds");
        tb_shutdown();
    } else {
        CHECK(0, "tb_init_fd initializes termbox2");
    }

    tb_os_close(master, slave);
    tb_os_report("test_64bit");
    return g_fails != 0 ? 1 : 0;
}
