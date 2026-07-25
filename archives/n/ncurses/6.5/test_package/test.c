#include <curses.h>
#include <stdio.h>

int main(void) {
    const char *version = curses_version();
    if (version == NULL || version[0] == '\0') {
        return 1;
    }
    printf("ncurses smoke test passed: %s\n", version);
    return 0;
}
