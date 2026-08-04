/* ncurses 6.4 静态库 smoke test: 验证链接和基本 API 可用 */
#include <stdio.h>
#include <ncurses.h>

int main(void) {
    int ret = 0;

    /* curses_version() 是真实库函数，任意环境都至少执行一次 ncurses 库代码
     * （NCURSES_VERSION 是编译期宏，打印它不构成库代码验证） */
    printf("ncurses version: %s\n", curses_version());

    /* setupterm 检测终端可用性，失败时 errret!=1 不调用 exit()，
     * 让我们能优雅返回 77（SKIP）。initscr 内部 setupterm 失败会直接
     * exit(EXIT_FAILURE)，无终端时到不了 return 77 分支。 */
    int errret = 0;
    setupterm(NULL, 1, &errret);
    if (errret != 1) {
        printf("setupterm: SKIP (no terminal available, errret=%d)\n", errret);
        return 77;
    }

    /* 尝试初始化 curses 模式 */
    WINDOW *w = initscr();
    if (w == NULL) {
        printf("initscr: SKIP (no terminal available on this platform)\n");
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
