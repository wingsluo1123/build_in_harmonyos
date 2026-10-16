/*
 * Port of upstream tests/test_mouse/test.php to native C.
 *
 * Upstream: init termbox on a memfd-backed tty via tb_init_rwfd, set
 * TB_INPUT_ALT | TB_INPUT_MOUSE, then for every (mode, action, wheel, motion,
 * coord) combination synthesize the xterm mouse escape sequence, feed it to
 * termbox and record the decoded (type, x, y, mod, key). The results are hashed
 * and compared against expected.ansi.
 *
 * Native: a real PTY pair; termbox is initialized on the slave (tb_init_fd)
 * and the exact same escape sequences are written into the master (bytes
 * written to the master are delivered to the slave's input, which termbox
 * reads). We assert the decoded event against the documented termbox2 mouse
 * decoding rules for all three encodings:
 *   vt200  \x1b[M Cb Cx Cy
 *   1006   \x1b[< Cb ; Cx ; Cy (M|m)
 *   1015   \x1b[ Cb ; Cx ; Cy M
 */
#include <stdio.h>
#include <string.h>

#include "tb_test_os.h"

enum { MODE_VT200, MODE_1006, MODE_1015, MODE_MAX };
enum { ACT_LEFT, ACT_MIDDLE, ACT_RIGHT, ACT_RELEASE, ACT_MAX };

static const char *const mode_name[MODE_MAX] = {"vt200", "1006", "1015"};
static const char *const act_name[ACT_MAX] = {"left", "middle", "right",
                                              "release"};
static const int act_bits[ACT_MAX] = {0, 1, 2, 3};
static const int coords[3][2] = {{0, 0}, {222, 222}, {1023, 1023}};

static int expected_key(int action, int wheel)
{
    switch (act_bits[action]) {
        case 0:
            return wheel ? TB_KEY_MOUSE_WHEEL_UP : TB_KEY_MOUSE_LEFT;
        case 1:
            return wheel ? TB_KEY_MOUSE_WHEEL_DOWN : TB_KEY_MOUSE_MIDDLE;
        case 2:
            return TB_KEY_MOUSE_RIGHT;
        default:
            return TB_KEY_MOUSE_RELEASE;
    }
}

int main(void)
{
    int master = -1, slave = -1;
    int init = 0;
    int rv;
    struct tb_event ev;
    int mode, action, wheel, motion, ci;
    int cases = 0;

    if (tb_os_open_pty(&master, &slave, 80, 24) != 0) {
        CHECK(0, "open PTY");
        tb_os_report("test_mouse");
        return 1;
    }

    rv = tb_os_init_fd(slave, &init);
    if (!init) {
        CHECK(0, "tb_init_fd initializes termbox2");
        tb_os_close(master, slave);
        tb_os_report("test_mouse");
        return 1;
    }

    CHECK(rv == TB_OK, "tb_init_fd initializes termbox2");
    CHECK(tb_set_input_mode(TB_INPUT_ALT | TB_INPUT_MOUSE) == TB_OK,
          "set TB_INPUT_ALT | TB_INPUT_MOUSE");

    for (mode = 0; mode < MODE_MAX; ++mode) {
        for (action = 0; action < ACT_MAX; ++action) {
            for (wheel = 0; wheel <= 1; ++wheel) {
                for (motion = 0; motion <= 1; ++motion) {
                    for (ci = 0; ci < 3; ++ci) {
                        int x = coords[ci][0], y = coords[ci][1];
                        int b, key, exp_mod, exp_x, exp_y;
                        char esc[64];
                        size_t len;
                        int ok;

                        if (wheel &&
                            !(action == ACT_LEFT || action == ACT_MIDDLE))
                            continue;
                        if (mode == MODE_VT200 && (x > 0xff || y > 0xff))
                            continue;

                        b = act_bits[action];
                        if (wheel)
                            b |= 0x40;
                        if (motion)
                            b |= 0x20;
                        if (mode != MODE_1006)
                            b += 0x20;

                        if (mode == MODE_VT200) {
                            esc[0] = '\x1b';
                            esc[1] = '[';
                            esc[2] = 'M';
                            esc[3] = (char)b;
                            esc[4] = (char)(0x21 + x);
                            esc[5] = (char)(0x21 + y);
                            len = 6;
                        } else if (mode == MODE_1006) {
                            len = (size_t)snprintf(
                                esc, sizeof(esc), "\x1b[<%d;%d;%d%c", b, x + 1,
                                y + 1,
                                action == ACT_RELEASE ? 'm' : 'M');
                        } else {
                            len = (size_t)snprintf(
                                esc, sizeof(esc), "\x1b[%d;%d;%dM", b, x + 1,
                                y + 1);
                        }

                        CHECK(tb_os_write_input(master, esc, len) == 0,
                              "write mouse escape");

                        memset(&ev, 0, sizeof(ev));
                        rv = tb_peek_event(&ev, 1500);

                        key = expected_key(action, wheel);
                        exp_mod = motion ? TB_MOD_MOTION : 0;

                        ok = (rv == 0 && ev.type == TB_EVENT_MOUSE &&
                              ev.key == key && ev.x == x && ev.y == y &&
                              ev.mod == exp_mod);
                        ++cases;
                        if (!ok) {
                            fprintf(stderr,
                                    "FAIL %s %s wheel=%d motion=%d (%d,%d): "
                                    "rv=%d type=%d key=%d x=%d y=%d mod=%d "
                                    "(expected type=%d key=%d x=%d y=%d "
                                    "mod=%d)\n",
                                    mode_name[mode], act_name[action], wheel,
                                    motion, x, y, rv, ev.type, ev.key, ev.x,
                                    ev.y, ev.mod, TB_EVENT_MOUSE, key, x, y,
                                    exp_mod);
                        }
                        CHECK(ok, "mouse event decoded as documented");
                    }
                }
            }
        }
    }

    CHECK(cases > 0, "exercised at least one mouse escape");
    fprintf(stderr, "test_mouse: %d mouse cases\n", cases);

    tb_shutdown();
    tb_os_close(master, slave);
    tb_os_report("test_mouse");
    return g_fails != 0 ? 1 : 0;
}
