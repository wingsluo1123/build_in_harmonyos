#include <ncurses.h>
#include <stdio.h>

int main(void) {
    /* Verify ncurses version API */
    const char *ver = curses_version();
    if (ver == NULL) {
        fprintf(stderr, "FAIL: curses_version() returned NULL\n");
        return 1;
    }
    printf("ncurses version: %s\n", ver);

    /* Verify terminfo lookup works without requiring a terminal */
    char buf[1024];
    int ret = tgetent(buf, "dumb");
    if (ret != 1) {
        fprintf(stderr, "FAIL: tgetent() returned %d\n", ret);
        return 1;
    }

    printf("ncurses API tests passed\n");
    return 0;
}
