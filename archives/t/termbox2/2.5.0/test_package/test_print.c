/*
 * Port of upstream tests/test_print/test.php to native C.
 *
 * Upstream: tb_init; tb_print multiline text, an escape byte and a tab;
 * tb_print out-of-bounds at (w,h) and (-1,-1) capturing the returned error;
 * a repeated 10-line print near the bottom-right; tb_present; screencap.
 *
 * Native: assert multiline/escape/tab prints round-trip TB_OK and that the
 * out-of-bounds prints return TB_ERR_OUT_OF_BOUNDS on a PTY.
 */
#include <stdio.h>
#include <string.h>

#include "tb_test_os.h"

int main(void)
{
    int master = -1, slave = -1;
    int init = 0;
    int rv;
    int w, h;
    int y = 0;
    int oob1, oob2;

    if (tb_os_open_pty(&master, &slave, 80, 24) != 0) {
        CHECK(0, "open PTY");
        tb_os_report("test_print");
        return 1;
    }

    rv = tb_os_init_fd(slave, &init);
    if (init) {
        CHECK(rv == TB_OK, "tb_init_fd initializes termbox2");
        w = tb_width();
        h = tb_height();
        CHECK(w > 0 && h > 0, "width/height positive");

        CHECK(tb_print(1, y++, 0, 0, "line1\nline2\nline3") == TB_OK,
              "tb_print multiline");
        y += 2;
        CHECK(tb_print(0, y++, 0, 0, "escape=[\x1b]") == TB_OK,
              "tb_print escape byte");
        CHECK(tb_print(0, y++, 0, 0, "tab=[\t]") == TB_OK, "tb_print tab");

        oob1 = tb_print(w, h, 0, 0, "oob1");
        oob2 = tb_print(-1, -1, 0, 0, "oob2");
        CHECK(oob1 == TB_ERR_OUT_OF_BOUNDS, "print(w,h) out of bounds");
        CHECK(oob2 == TB_ERR_OUT_OF_BOUNDS, "print(-1,-1) out of bounds");

        /* upstream: tb_print(w-5, h-5, ..., str_repeat("0123456789\\n", 10)) --
         * a single multiline print that renders past the bottom edge. It is
         * only expected not to fail with a non-bounds error. */
        {
            static const char *tenlines =
                "0123456789\n0123456789\n0123456789\n0123456789\n0123456789\n"
                "0123456789\n0123456789\n0123456789\n0123456789\n0123456789";
            int mr = tb_print(w - 5, h - 5, 0, 0, tenlines);
            CHECK(mr == TB_OK || mr == TB_ERR_OUT_OF_BOUNDS,
                  "multiline near bottom edge renders without internal error");
        }
        CHECK(tb_present() == TB_OK, "tb_present succeeds");
        tb_shutdown();
    } else {
        CHECK(0, "tb_init_fd initializes termbox2");
    }

    tb_os_close(master, slave);
    tb_os_report("test_print");
    return g_fails != 0 ? 1 : 0;
}
