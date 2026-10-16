/*
 * Port of upstream tests/test_resize/test.php to native C.
 *
 * Upstream: tb_init; tb_width/height; raise(SIGWINCH); tb_peek_event(1000);
 * report the RESIZE event (type, old w/h, new w/h); present; screencap.
 *
 * Native: termbox2 installs a SIGWINCH handler and a resize pipe during init,
 * so raising SIGWINCH on a PTY-session should yield a TB_EVENT_RESIZE event
 * from tb_peek_event. We assert the event arrives with the new dimensions.
 */
#include <signal.h>
#include <stdio.h>
#include <string.h>

#include "tb_test_os.h"

int main(void)
{
    int master = -1, slave = -1;
    int init = 0;
    int rv;
    struct tb_event ev;
    int ow, oh;

    if (tb_os_open_pty(&master, &slave, 80, 24) != 0) {
        CHECK(0, "open PTY");
        tb_os_report("test_resize");
        return 1;
    }

    rv = tb_os_init_fd(slave, &init);
    if (init) {
        CHECK(rv == TB_OK, "tb_init_fd initializes termbox2");
        ow = tb_width();
        oh = tb_height();
        CHECK(ow > 0 && oh > 0, "initial width/height are positive");

        /* upstream raise(SIGWINCH) -> resize event via tb_peek_event */
        CHECK(raise(SIGWINCH) == 0, "raise(SIGWINCH)");
        memset(&ev, 0, sizeof(ev));
        rv = tb_peek_event(&ev, 1500);
        CHECK(rv == 0, "tb_peek_event returns after SIGWINCH");
        CHECK(ev.type == TB_EVENT_RESIZE, "SIGWINCH yields a RESIZE event");
        CHECK(ev.w > 0 && ev.h > 0, "resize event reports new dimensions");

        CHECK(tb_present() == TB_OK, "tb_present succeeds");
        tb_shutdown();
    } else {
        CHECK(0, "tb_init_fd initializes termbox2");
    }

    tb_os_close(master, slave);
    tb_os_report("test_resize");
    return g_fails != 0 ? 1 : 0;
}
