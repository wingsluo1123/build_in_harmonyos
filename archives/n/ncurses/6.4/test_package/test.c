#include <curses.h>
#include <stdio.h>

int main(void) {
    /* Verify ncursesw headers are available and linkable */
    printf("ncurses version: %s\n", NCURSES_VERSION);
    return 0;
}