/*
 * tb_test_os.h - shared helper for porting termbox2's upstream tests/
 *                 test_<name>/test.php cases to native C so they can be
 *                 executed on headless HarmonyOS PC over a PTY.
 *
 * The upstream test suite is a PHP-FFI + X11 (Xvfb/xterm/xvkbd) screen-capture
 * harness that is not available on OHOS/aarch64. Each test's real logic is a
 * sequence of termbox2 C API calls against the shared/static library; we port
 * each test to C and drive the same API over a PTY (tb_init_fd), which
 * reproduces the upstream behaviour on a headless target.
 */

#ifndef TB_TEST_OS_H
#define TB_TEST_OS_H

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <termios.h>
#include <unistd.h>

#include <termbox2.h>

static int g_checks;
static int g_fails;

#define CHECK(cond, msg)                          \
    do {                                          \
        ++g_checks;                               \
        if (!(cond)) {                            \
            ++g_fails;                            \
            fprintf(stderr, "FAIL %s: %s\n",      \
                    __func__, (msg));             \
        }                                         \
    } while (0)

/* Open a PTY pair (master + slave), set its window size, and export the fds.
 * Returns 0 on success, -1 on failure. */
static int tb_os_open_pty(int *master, int *slave, int cols, int rows)
{
    struct winsize ws;
    char *name;

    *master = *slave = -1;
    *master = posix_openpt(O_RDWR | O_NOCTTY);
    if (*master < 0)
        return -1;
    if (grantpt(*master) != 0)
        return -1;
    if (unlockpt(*master) != 0)
        return -1;
    name = ptsname(*master);
    if (name == NULL)
        return -1;
    *slave = open(name, O_RDWR | O_NOCTTY);
    if (*slave < 0)
        return -1;

    memset(&ws, 0, sizeof(ws));
    ws.ws_col = (unsigned short)cols;
    ws.ws_row = (unsigned short)rows;
    ioctl(*slave, TIOCSWINSZ, &ws);
    /* termbox2 falls back to a built-in terminal when no terminfo is present;
     * a well-known TERM keeps the caps lookup deterministic. */
    if (setenv("TERM", "xterm", 1) != 0)
        return -1;
    return 0;
}

/* Init termbox2 on a PTY slave with a single read/write fd. termbox reads and
 * writes through this fd; bytes written to the PTY master are delivered to the
 * slave's input and read by termbox. */
static int tb_os_init_fd(int slave, int *init)
{
    int rv = tb_init_fd(slave);
    *init = (rv == TB_OK);
    return rv;
}

/* Write raw bytes into the PTY master (delivered to the slave's input). */
static int tb_os_write_input(int master, const char *data, size_t len)
{
    size_t off = 0;
    while (off < len) {
        ssize_t n = write(master, data + off, len - off);
        if (n <= 0)
            return -1;
        off += (size_t)n;
    }
    return 0;
}

/* Emit the same style of PASS/FAIL summary the upstream harness prints. */
static void tb_os_report(const char *name)
{
    if (g_fails != 0) {
        fprintf(stderr, "%s: %d/%d checks failed\n", name, g_fails, g_checks);
        exit(1);
    }
    printf("%s: PASS (%d checks)\n", name, g_checks);
}

static void tb_os_close(int master, int slave)
{
    if (slave >= 0)
        close(slave);
    if (master >= 0)
        close(master);
}

#endif /* TB_TEST_OS_H */
