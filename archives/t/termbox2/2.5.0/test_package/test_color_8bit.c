/*
 * Port of upstream tests/test_color_8bit/test.php to native C.
 *
 * Upstream: tb_init; tb_width/height; for each output mode
 * TB_OUTPUT_NORMAL/256/216/GRAYSCALE call tb_set_output_mode, tb_print the
 * mode name and a sweep of fg colors, tb_present; screencap.
 *
 * Native: drive the same API on a PTY and assert each mode switch + print +
 * present round-trips TB_OK.
 */
#include <stdio.h>

#include "tb_test_os.h"

static void test_mode(int mode, const char *mode_name, int n, int w)
{
    int x = 0, y = 1, fg;
    char txt[8];

    CHECK(tb_set_output_mode(mode) == TB_OK, mode_name);
    CHECK(tb_print(x, y, TB_DEFAULT, TB_DEFAULT, mode_name) == TB_OK,
          mode_name);
    ++y;
    for (fg = 0; fg <= n; ++fg) {
        uintattr_t cfg;
        if (mode == TB_OUTPUT_256) {
            if (fg == 0)
                cfg = TB_DEFAULT;
            else if (fg == 1)
                cfg = TB_HI_BLACK;
            else
                cfg = (uintattr_t)(fg - 1);
        } else {
            cfg = (uintattr_t)fg;
        }
        snprintf(txt, sizeof(txt), "\xe2\x96\x80");
        if (x + 1 > w) {
            x = 0;
            ++y;
        }
        CHECK(tb_print(x, y, cfg, TB_DEFAULT, txt) == TB_OK, mode_name);
        x += 1;
    }
    CHECK(tb_present() == TB_OK, mode_name);
}

int main(void)
{
    int master = -1, slave = -1;
    int init = 0;
    int w;

    if (tb_os_open_pty(&master, &slave, 80, 24) != 0) {
        CHECK(0, "open PTY");
        tb_os_report("test_color_8bit");
        return 1;
    }

    if (tb_os_init_fd(slave, &init) == TB_OK && init) {
        w = tb_width();
        CHECK(w > 0, "tb_width()>0");
        test_mode(TB_OUTPUT_NORMAL, "TB_OUTPUT_NORMAL", 8, w);
        test_mode(TB_OUTPUT_256, "TB_OUTPUT_256", 256, w);
        test_mode(TB_OUTPUT_216, "TB_OUTPUT_216", 216, w);
        test_mode(TB_OUTPUT_GRAYSCALE, "TB_OUTPUT_GRAYSCALE", 24, w);
        tb_shutdown();
    } else {
        CHECK(0, "tb_init_fd initializes termbox2");
    }

    tb_os_close(master, slave);
    tb_os_report("test_color_8bit");
    return g_fails != 0 ? 1 : 0;
}
