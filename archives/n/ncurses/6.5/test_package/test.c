#include <stdio.h>
#include <ncurses.h>

int main(void) {
    printf("ncurses version: %s\n", curses_version());
    printf("ncurses test passed: library is available\n");
    return 0;
}
