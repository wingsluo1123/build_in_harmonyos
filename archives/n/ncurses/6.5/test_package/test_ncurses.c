#include <curses.h>
#include <term.h>

#include <stdio.h>

static int putch(int ch) {
    return ch;
}

int main(void) {
    int err = 0;
    const char *clear_seq;

    if (setupterm("xterm-256color", 1, &err) != OK) {
        fprintf(stderr, "setupterm failed: %d\n", err);
        return 1;
    }

    clear_seq = tigetstr("clear");
    if (clear_seq == NULL || clear_seq == (char *)-1) {
        fprintf(stderr, "clear capability missing\n");
        return 1;
    }

    tputs(clear_seq, 1, putch);
    printf("%s\n", curses_version());
    return 0;
}
