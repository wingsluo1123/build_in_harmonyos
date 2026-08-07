/*
 * ncurses/6.5 test_package — 实质调用 ncurses API (R34)
 *
 * 1) curses_version(): 真实链接 libncursesw, 校验版本字符串
 * 2) tputs(): 真实调用 terminfo 输出函数 (无需终端)
 */
#include <stdio.h>
#include <string.h>
#include <curses.h>
#include <term.h>

/* tputs 的 putc 回调 */
static int swallow(int ch)
{
    (void)ch;
    return OK;
}

int main(void)
{
    const char *ver = curses_version();

    if (ver == NULL || strncmp(ver, "ncurses", 7) != 0) {
        fprintf(stderr, "FAIL: curses_version() = %s\n", ver ? ver : "()");
        return 1;
    }
    if (tputs("0", 1, swallow) == ERR) {
        fprintf(stderr, "FAIL: tputs() returned ERR\n");
        return 1;
    }
    printf("ncurses %s OK (curses_version=%s)\n", NCURSES_VERSION, ver);
    return 0;
}
