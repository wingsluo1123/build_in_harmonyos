#include <curses.h>
#include <stdio.h>
#include <string.h>
#include <unctrl.h>

int main(void)
{
    const char *version = curses_version();
    const char *left_key = keyname(KEY_LEFT);
    const char *newline = unctrl('\n');

    if (version == NULL || version[0] == '\0') {
        return 1;
    }
    if (strstr(version, "ncurses") == NULL) {
        return 2;
    }
    if (left_key == NULL || strcmp(left_key, "KEY_LEFT") != 0) {
        return 3;
    }
    if (newline == NULL || strcmp(newline, "^J") != 0) {
        return 4;
    }

    printf("ncurses runtime: %s; key=%s; unctrl=%s\n", version, left_key, newline);
    return 0;
}
