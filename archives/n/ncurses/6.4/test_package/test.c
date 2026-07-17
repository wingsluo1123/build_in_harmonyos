#include <ncurses.h>
#include <stdio.h>

int main(void) {
    printf("ncurses: linked OK, version: %s\n", NCURSES_VERSION);
    return 0;
}
