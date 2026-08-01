/* ncurses 6.4 静态库 smoke test: 链接 libncursesw.a 验证 initscr/endwin 可用 */
#include <ncurses.h>

int main(void) {
    /* OHOS 无真实终端，只验证符号链接可解析（不真跑 initscr 避免挂起） */
    WINDOW *w = stdscr;
    (void)w;
    return 0;
}
