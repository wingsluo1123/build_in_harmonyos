/*
 * Port of upstream tests/test_large_input/test.php to native C.
 *
 * Upstream: init termbox with a fake memfd-backed tty via tb_init_rwfd, set
 * TB_INPUT_ALT, write ceil(TB_OPT_READ_BUF/3) up-arrow escape sequences
 * ("\x1bOA") into the read end, then drain tb_peek_event counting the
 * TB_KEY_ARROW_UP events until no more arrive, and report the count.
 *
 * Native: we use a real PTY pair and init termbox2 on the slave
 * (tb_init_fd); bytes written to the master are delivered to the slave's
 * input, which termbox reads. We write the up-arrow bytes into the master and
 * count the resulting key events, exactly reproducing the upstream flow.
 */
#include <stdio.h>
#include <string.h>

#include "tb_test_os.h"

int main(void)
{
    int master = -1, slave = -1;
    int init = 0;
    int rv;
    int up_arrow_count = 0;
    struct tb_event ev;
    char input[512];
    int n, i, nbytes;

    if (tb_os_open_pty(&master, &slave, 80, 24) != 0) {
        CHECK(0, "open PTY");
        tb_os_report("test_large_input");
        return 1;
    }

    rv = tb_os_init_fd(slave, &init);
    if (init) {
        CHECK(rv == TB_OK, "tb_init_fd initializes termbox2");

        /* ceil(TB_OPT_READ_BUF / 3) up-arrow sequences fill the read buffer */
        n = (TB_OPT_READ_BUF + 2) / 3;
        nbytes = 0;
        for (i = 0; i < n; ++i) {
            input[nbytes++] = '\x1b';
            input[nbytes++] = 'O';
            input[nbytes++] = 'A';
        }

        CHECK(tb_set_input_mode(TB_INPUT_ALT) == TB_OK, "set TB_INPUT_ALT");
        CHECK(tb_os_write_input(master, input, (size_t)nbytes) == 0,
              "write up-arrow bytes to input");

        do {
            memset(&ev, 0, sizeof(ev));
            rv = tb_peek_event(&ev, 1500);
            if (rv == 0 && ev.type == TB_EVENT_KEY &&
                ev.key == TB_KEY_ARROW_UP) {
                up_arrow_count += 1;
            }
        } while (rv == 0);
        CHECK(up_arrow_count > 0, "drained at least one ARROW_UP event");
        CHECK(up_arrow_count == n, "all up-arrow events counted");
        tb_shutdown();
    } else {
        CHECK(0, "tb_init_fd initializes termbox2");
    }

    tb_os_close(master, slave);
    tb_os_report("test_large_input");
    return g_fails != 0 ? 1 : 0;
}
