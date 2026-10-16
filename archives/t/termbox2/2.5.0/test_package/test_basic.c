/*
 * Port of upstream tests/test_basic/test.php to native C.
 *
 * Upstream: tb_init(); tb_width/height(); tb_version(); tb_printf();
 * inject Ctrl-A (upstream drives xvkbd under X11), then tb_peek_event and
 * assert the key event came back; tb_printf_ex; tb_present; screencap.
 *
 * Native: we init termbox2 on the PTY slave (tb_init_fd), write '\x01'
 * (Ctrl-A) into the master (bytes written to the master are delivered to the
 * slave's input, which termbox reads), and assert the key event is returned.
 * The screen-capture diff is replaced by direct assertions on the real API
 * results.
 */
#include <stdio.h>
#include <string.h>

#include "tb_test_os.h"

int main(void)
{
    int master = -1, slave = -1;
    struct tb_event ev;
    int init = 0;
    int rv;

    if (tb_os_open_pty(&master, &slave, 80, 24) != 0) {
        CHECK(0, "open PTY");
        tb_os_report("test_basic");
        return 1;
    }

    rv = tb_os_init_fd(slave, &init);
    if (init) {
        CHECK(rv == TB_OK, "tb_init_fd initializes termbox2");
        CHECK(strcmp(tb_version(), "2.5.0") == 0, "tb_version() == 2.5.0");
        CHECK(tb_width() > 0, "tb_width() > 0");
        CHECK(tb_height() > 0, "tb_height() > 0");

        /* mirrors upstream tb_printf(0, y++, ...) */
        CHECK(tb_printf(0, 0, 0, 0, "has_version=%s",
                        strlen(tb_version()) > 0 ? "y" : "n") >= 0,
              "tb_printf version line");

        /* Inject Ctrl-A (upstream uses xvkbd '\Ca') as a raw input byte. A
         * raw 0x01 control byte is reported as a key event keyed
         * TB_KEY_CTRL_A (0x01) with ch==0 and mod|CTRL. */
        CHECK(tb_os_write_input(master, "\x01", 1) == 0, "inject Ctrl-A");
        memset(&ev, 0, sizeof(ev));
        rv = tb_peek_event(&ev, 1500);
        CHECK(rv == 0, "tb_peek_event returns an event");
        CHECK(ev.type == TB_EVENT_KEY, "Ctrl-A produces a key event");
        CHECK(ev.key == TB_KEY_CTRL_A, "Ctrl-A key event reports TB_KEY_CTRL_A");
        CHECK(ev.ch == 0, "Ctrl-A key event has ch==0");
        CHECK((ev.mod & TB_MOD_CTRL) != 0, "Ctrl-A key event carries CTRL mod");

        CHECK(tb_present() == TB_OK, "tb_present succeeds");
        tb_shutdown();
    } else {
        CHECK(0, "tb_init_fd initializes termbox2");
    }

    tb_os_close(master, slave);
    tb_os_report("test_basic");
    return g_fails != 0 ? 1 : 0;
}
