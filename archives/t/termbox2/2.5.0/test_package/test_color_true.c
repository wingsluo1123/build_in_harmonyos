/*
 * Port of upstream tests/test_color_true/test.php to native C.
 *
 * Upstream: skip unless tb_has_truecolor(); then tb_init;
 * tb_set_output_mode(TB_OUTPUT_TRUECOLOR); tb_print a table of CSS-ish true
 * colors, bold/underline/italic variants and a full fg/bg grid; tb_present;
 * screencap.
 *
 * Native: the packaged library is built with TB_LIB_OPTS (TB_OPT_EGC/truetype
 * color support), so tb_has_truecolor() is true and the test runs. We assert
 * the truecolor mode switch and each print round-trips TB_OK on a PTY.
 */
#include <stdio.h>

#include "tb_test_os.h"

int main(void)
{
    int master = -1, slave = -1;
    int init = 0;
    int rv;
    int x, y;

    CHECK(tb_has_truecolor() != 0, "tb_has_truecolor()");

    if (tb_os_open_pty(&master, &slave, 80, 24) != 0) {
        CHECK(0, "open PTY");
        tb_os_report("test_color_true");
        return 1;
    }

    rv = tb_os_init_fd(slave, &init);
    if (init) {
        CHECK(rv == TB_OK, "tb_init_fd initializes termbox2");
        CHECK(tb_width() > 0, "tb_width()>0");
        CHECK(tb_set_output_mode(TB_OUTPUT_TRUECOLOR) == TB_OK,
              "set TRUECOLOR mode");

        /* a representative sample of the upstream css-colors table */
        CHECK(tb_print(0, 0, 0xfaebd7, TB_DEFAULT,
                       "antiquewhite, ") == TB_OK, "truecolor print");
        CHECK(tb_print(0, 1, 0x0000ff, TB_DEFAULT, "blue, ") == TB_OK,
              "truecolor print");
        CHECK(tb_print(0, 2, TB_DEFAULT, 0x00ff00, "default on green, ") == TB_OK,
              "truecolor bg");

        /* bold/underline/italic variants (mirrors upstream) */
        x = 0;
        y = 3;
        CHECK(tb_printf(x, y, 0x808080 | TB_BOLD, TB_DEFAULT,
                        "yes bold (#%06x)", 0x808080 | TB_BOLD) >= 0,
              "truecolor bold");
        CHECK(tb_printf(x, ++y, 0x808080 | TB_UNDERLINE, TB_DEFAULT,
                        "yes underline (#%06x)", 0x808080 | TB_UNDERLINE) >= 0,
              "truecolor underline");
        CHECK(tb_printf(x, ++y, 0x808080 | TB_ITALIC, TB_DEFAULT,
                        "yes italic (#%06x)", 0x808080 | TB_ITALIC) >= 0,
              "truecolor italic");

        CHECK(tb_present() == TB_OK, "tb_present succeeds");
        tb_shutdown();
    } else {
        CHECK(0, "tb_init_fd initializes termbox2");
    }

    tb_os_close(master, slave);
    tb_os_report("test_color_true");
    return g_fails != 0 ? 1 : 0;
}
