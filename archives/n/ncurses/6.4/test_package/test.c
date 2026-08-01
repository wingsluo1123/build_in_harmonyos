/* ncurses 6.4 静态库 smoke test: 验证链接和基本 API 可用 */
#include <stdio.h>
#include <ncurses.h>

int main(void) {
    int ret = 0;

    /* curses_version() 是真实库函数，任意环境都至少执行一次 ncurses 库代码
     * （NCURSES_VERSION 是编译期宏，打印它不构成库代码验证） */
    printf("ncurses version: %s\n", curses_version());

    /* 尝试初始化 curses 模式，OHOS 无真实终端时 initscr 返回 NULL */
    WINDOW *w = initscr();
    if (w == NULL) {
        printf("initscr: SKIP (no terminal available on this platform)\n");
        /* 无终端分支返回专用 SKIP 退出码 77，test() 按跳过处理（R34 反空转） */
        return 77;
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
