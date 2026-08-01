/* ncurses 6.4 静态库 smoke test: 验证链接和基本 API 可用 */
#include <stdio.h>
#include <ncurses.h>

int main(void) {
    int ret = 0;

    printf("ncurses version: %s\n", NCURSES_VERSION);

    /* 尝试初始化 curses 模式，OHOS 无真实终端时 initscr 返回 NULL */
    WINDOW *w = initscr();
    if (w == NULL) {
        printf("initscr: SKIP (no terminal available on this platform)\n");
        /* 即使无终端，链接验证已通过（前面已打印 NCURSES_VERSION 符号） */
        return 0;
    }

    /* 基本 API 调用验证 */
    if (has_colors()) {
        ret |= start_color();
    }

    /* 输出终端尺寸信息验证 getmaxyx 宏 */
    int rows, cols;
    getmaxyx(stdscr, rows, cols);
    printf("terminal: %dx%d\n", rows, cols);

    /* 正常退出 curses 模式 */
    endwin();

    printf("ncurses smoke test PASSED\n");
    return ret;
}
