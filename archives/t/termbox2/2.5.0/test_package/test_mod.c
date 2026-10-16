/*
 * Port of upstream tests/test_mod/test.php to native C.
 *
 * Upstream: init termbox on a fake memfd-backed tty via tb_init_rwfd, set
 * TB_INPUT_ALT, write seven "\x1b[1;<m>A" modifier escape sequences, drain
 * tb_peek_event collecting (type, mod, key, ch) for each, and report them.
 *
 * Native: a real PTY pair; termbox is initialized on the slave (tb_init_fd)
 * and we write the exact upstream modifier sequences into the master (bytes
 * written to the master are delivered to the slave's input) and verify the
 * reported TB_KEY_ARROW_UP modifiers match the documented mapping:
 *   1;2A -> SHIFT, 1;3A -> ALT, 1;4A -> ALT|SHIFT, 1;5A -> CTRL,
 *   1;6A -> CTRL|SHIFT, 1;7A -> CTRL|ALT, 1;8A -> CTRL|ALT|SHIFT.
 */
#include <stdio.h>
#include <string.h>

#include "tb_test_os.h"

#define N_MODS 7

static const char *const mod_seq[N_MODS] = {
    "\x1b[1;2A", "\x1b[1;3A", "\x1b[1;4A", "\x1b[1;5A",
    "\x1b[1;6A", "\x1b[1;7A", "\x1b[1;8A",
};
static const int mod_expected[N_MODS] = {
    TB_MOD_SHIFT,
    TB_MOD_ALT,
    TB_MOD_ALT | TB_MOD_SHIFT,
    TB_MOD_CTRL,
    TB_MOD_CTRL | TB_MOD_SHIFT,
    TB_MOD_CTRL | TB_MOD_ALT,
    TB_MOD_CTRL | TB_MOD_ALT | TB_MOD_SHIFT,
};

int main(void)
{
    int master = -1, slave = -1;
    int init = 0;
    int rv;
    struct tb_event ev;
    int collected[N_MODS];
    int count = 0;
    int i;

    if (tb_os_open_pty(&master, &slave, 80, 24) != 0) {
        CHECK(0, "open PTY");
        tb_os_report("test_mod");
        return 1;
    }

    rv = tb_os_init_fd(slave, &init);
    if (init) {
        CHECK(rv == TB_OK, "tb_init_fd initializes termbox2");
        CHECK(tb_set_input_mode(TB_INPUT_ALT) == TB_OK, "set TB_INPUT_ALT");

        for (i = 0; i < N_MODS && count < N_MODS; ++i) {
            size_t len = strlen(mod_seq[i]);
            CHECK(tb_os_write_input(master, mod_seq[i], len) == 0,
                  "write modifier sequence");
            do {
                memset(&ev, 0, sizeof(ev));
                rv = tb_peek_event(&ev, 1500);
                if (rv == 0 && ev.type == TB_EVENT_KEY) {
                    collected[count++] = ev.mod;
                }
            } while (rv == 0 && count <= i);
        }

        CHECK(count == N_MODS, "received one key event per modifier sequence");
        for (i = 0; i < count && i < N_MODS; ++i) {
            if (collected[i] != mod_expected[i]) {
                fprintf(stderr,
                        "mod[%d]=%d expected %d\n", i, collected[i],
                        mod_expected[i]);
                ++g_checks;
                ++g_fails;
            }
        }
        tb_shutdown();
    } else {
        CHECK(0, "tb_init_fd initializes termbox2");
    }

    tb_os_close(master, slave);
    tb_os_report("test_mod");
    return g_fails != 0 ? 1 : 0;
}
