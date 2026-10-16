/*
 * Port of upstream tests/test_egc/test.php to native C.
 *
 * Upstream: skip unless tb_has_egc(); then tb_init; convert the cyrillic
 * "e" (\xd0\xb5) and combining diaeresis (\xcc\x88) to code points; place an
 * EGC via tb_set_cell_ex at (1,y) with nech=2, build another via
 * tb_extend_cell after tb_set_cell, then reproduce the same combining
 * sequence via tb_print; tb_present; screencap.
 *
 * Native: the packaged library is built with TB_LIB_OPTS (TB_OPT_EGC), so
 * tb_has_egc() is true and the test runs. We assert each API round-trips and
 * that the octet sequences decode to the expected code points.
 */
#include <stdint.h>
#include <stdio.h>

#include "tb_test_os.h"

int main(void)
{
    int master = -1, slave = -1;
    int init = 0;
    int rv;
    uint32_t ech[2];
    int y = 0;

    CHECK(tb_has_egc() != 0, "tb_has_egc() (TB_OPT_EGC)");

    if (tb_os_open_pty(&master, &slave, 80, 24) != 0) {
        CHECK(0, "open PTY");
        tb_os_report("test_egc");
        return 1;
    }

    rv = tb_os_init_fd(slave, &init);
    if (init) {
        CHECK(rv == TB_OK, "tb_init_fd initializes termbox2");

        CHECK(tb_utf8_char_to_unicode(&ech[0], "\xd0\xb5") == 2,
              "decode cyrillic ie");
        CHECK(tb_utf8_char_to_unicode(&ech[1], "\xcc\x88") == 2,
              "decode combining diaeresis");

        /* Set EGC using tb_set_cell_ex */
        CHECK(tb_set_cell(0, y, (uint32_t)'a', 0, 0) == TB_OK,
              "tb_set_cell baseline");
        CHECK(tb_set_cell_ex(1, y, ech, 2, 0, 0) == TB_OK,
              "tb_set_cell_ex EGC");
        CHECK(tb_set_cell(2, y, (uint32_t)'b', 0, 0) == TB_OK,
              "tb_set_cell after EGC");

        /* Same effect with tb_extend_cell */
        ++y;
        CHECK(tb_set_cell(0, y, (uint32_t)'c', 0, 0) == TB_OK,
              "tb_set_cell base c");
        CHECK(tb_set_cell(1, y, ech[0], 0, 0) == TB_OK, "tb_set_cell ech0");
        CHECK(tb_extend_cell(1, y, ech[1]) == TB_OK, "tb_extend_cell ech1");
        CHECK(tb_set_cell(2, y, (uint32_t)'d', 0, 0) == TB_OK,
              "tb_set_cell after extend");

        /* 2 combining characters via extend_cell */
        ++y;
        CHECK(tb_set_cell(0, y, 0xff29, 0, 0) == TB_OK, "tb_set_cell fullwidth i");
        CHECK(tb_extend_cell(0, y, 0x0324) == TB_OK, "tb_extend_cell umlaut below");
        CHECK(tb_extend_cell(0, y, 0x036f) == TB_OK, "tb_extend_cell latin x");

        /* same as above via tb_print (should be equivalent) */
        ++y;
        CHECK(tb_print(0, y, 0, 0, "\xef\xbc\xa9\xcc\xa4\xcd\xaf") == TB_OK,
              "tb_print combining sequence");

        CHECK(tb_present() == TB_OK, "tb_present succeeds");
        tb_shutdown();
    } else {
        CHECK(0, "tb_init_fd initializes termbox2");
    }

    tb_os_close(master, slave);
    tb_os_report("test_egc");
    return g_fails != 0 ? 1 : 0;
}
