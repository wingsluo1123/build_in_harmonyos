#define _XOPEN_SOURCE 600

#ifndef __OHOS__
#error "test_ohos_pty must be compiled for HarmonyOS"
#endif

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/utsname.h>
#include <termios.h>
#include <unistd.h>

#include <termbox2.h>

static int checks;
static int failures;

static void check(int condition, const char *message)
{
    ++checks;
    if (!condition) {
        ++failures;
        fprintf(stderr, "FAIL: %s (errno=%d: %s)\n",
                message, errno, strerror(errno));
    }
}

int main(void)
{
    struct winsize size = {0};
    struct utsname system_info;
    struct tb_cell *cells;
    char *slave_name;
    int master_fd = -1;
    int slave_fd = -1;
    int initialized = 0;
    int result;

    check(uname(&system_info) == 0, "uname succeeds on HarmonyOS");
    check(strcmp(system_info.machine, "aarch64") == 0,
          "HarmonyOS device architecture is aarch64");

    master_fd = posix_openpt(O_RDWR | O_NOCTTY);
    check(master_fd >= 0, "posix_openpt creates a PTY master");
    if (master_fd < 0)
        goto done;

    check(grantpt(master_fd) == 0, "grantpt succeeds");
    check(unlockpt(master_fd) == 0, "unlockpt succeeds");
    slave_name = ptsname(master_fd);
    check(slave_name != NULL, "ptsname returns a slave path");
    if (slave_name == NULL)
        goto done;

    slave_fd = open(slave_name, O_RDWR | O_NOCTTY);
    check(slave_fd >= 0, "PTY slave opens");
    if (slave_fd < 0)
        goto done;

    size.ws_col = 93;
    size.ws_row = 31;
    check(ioctl(slave_fd, TIOCSWINSZ, &size) == 0,
          "TIOCSWINSZ configures the PTY");
    check(setenv("TERM", "xterm", 1) == 0, "TERM is set to a built-in terminal");

    result = tb_init_fd(slave_fd);
    check(result == 0, "tb_init_fd initializes termbox2 on a HarmonyOS PTY");
    if (result != 0)
        goto done;
    initialized = 1;

    check(tb_width() == 93 && tb_height() == 31,
          "termbox2 reads the PTY window size");
    result = tb_set_input_mode(TB_INPUT_ESC);
    check(result >= 0, "input mode is selectable");
    result = tb_set_output_mode(TB_OUTPUT_256);
    check(result >= 0, "256-color output mode is selectable");

    check(tb_set_clear_attrs(TB_WHITE, TB_BLUE) == 0, "clear attrs can be set");
    check(tb_clear() == 0, "clear succeeds");
    cells = tb_cell_buffer();
    check(cells != NULL && cells[0].ch == (uint32_t)' ' &&
              cells[0].bg == TB_BLUE,
          "clear attributes reach the back buffer");

    check(tb_set_cell(0, 0, (uint32_t)'T', TB_GREEN | TB_BOLD, TB_DEFAULT) == 0,
          "tb_set_cell writes a cell");
    cells = tb_cell_buffer();
    check(cells != NULL && cells[0].ch == (uint32_t)'T' &&
              cells[0].fg == (TB_GREEN | TB_BOLD),
          "cell update is present in the back buffer");
    check(tb_present() == 0, "tb_present synchronizes to the PTY");

done:
    if (initialized)
        tb_shutdown();
    if (master_fd >= 0)
        close(master_fd);
    if (slave_fd >= 0)
        close(slave_fd);

    if (failures != 0) {
        fprintf(stderr, "termbox2 OHOS PTY: %d/%d checks failed\n",
                failures, checks);
        return 1;
    }

    printf("termbox2 OHOS PTY: PASS (%d assertions)\n", checks);
    return 0;
}
