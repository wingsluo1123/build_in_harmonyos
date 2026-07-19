/*
 * test_ncurses.c — verify ncurses library is linkable.
 *
 * Tests that the wide-character ncurses header is present and
 * that basic initscr() / endwin() symbols resolve at link time.
 * We do NOT call them (no terminal in CI) — linking is sufficient.
 */
#include <ncurses.h>
#include <stdio.h>

int main(void) {
    printf("ncurses: initscr = %p\n", (void *)initscr);
    printf("ncurses: endwin  = %p\n", (void *)endwin);
    printf("ncurses: stdscr  = %p\n", (void *)stdscr);
    printf("Hello from ncurses test!\n");
    return 0;
}