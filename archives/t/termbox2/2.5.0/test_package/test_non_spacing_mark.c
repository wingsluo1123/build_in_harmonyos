/*
 * Port of upstream tests/test_non_spacing_mark/test.php to native C.
 *
 * Upstream: skip unless tb_has_egc(); tb_init; tb_print two lines containing
 * combining marks (STARG lambda-combining STARG, a-umlaut r-umlaut, a-plus,
 * b-plus), tb_present; screencap. Verifies non-spacing marks compose as EGC.
 *
 * Native: the packaged library has TB_OPT_EGC, so tb_has_egc() is true and the
 * test runs; assert each print round-trips TB_OK on a PTY.
 */
#include <stdio.h>

#include "tb_test_os.h"

int main(void)
{
    int master = -1, slave = -1;
    int init = 0;
    int rv;

    CHECK(tb_has_egc() != 0, "tb_has_egc() (TB_OPT_EGC)");

    if (tb_os_open_pty(&master, &slave, 80, 24) != 0) {
        CHECK(0, "open PTY");
        tb_os_report("test_non_spacing_mark");
        return 1;
    }

    rv = tb_os_init_fd(slave, &init);
    if (init) {
        CHECK(rv == TB_OK, "tb_init_fd initializes termbox2");
        CHECK(tb_print(0, 0, 0, 0, "STARG\xce\x9b\xcc\x8aTE SG-1") == TB_OK,
              "print EGC line 1");
        CHECK(tb_print(0, 1, 0, 0,
                       "a = v\xcc\x87 = r\xcc\x88, a\xe2\x83\x91 "
                       "\xe2\x8a\xa5 b\xe2\x83\x91") == TB_OK,
              "print EGC line 2");
        CHECK(tb_present() == TB_OK, "tb_present succeeds");
        tb_shutdown();
    } else {
        CHECK(0, "tb_init_fd initializes termbox2");
    }

    tb_os_close(master, slave);
    tb_os_report("test_non_spacing_mark");
    return g_fails != 0 ? 1 : 0;
}
