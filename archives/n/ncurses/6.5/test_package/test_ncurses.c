#include <ncursesw/curses.h>
#include <stdio.h>

int main() {
    /* Verify ncursesw (wide character) API is available */
    printf("ncurses version: %s\n", NCURSES_VERSION);
    printf("wide char support: yes\n");
    return 0;
}
