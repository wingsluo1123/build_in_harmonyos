/* Minimal ncurses test — links against libncursesw.a.
 * Verifies the static archive and wide-char headers are usable.
 * initscr() may fail without a real tty; we only need it to compile/link.
 */
#include <ncurses.h>

int main(void) {
    /* initscr returns NULL on failure (no tty); that's fine for a link test */
    SCREEN *s = newterm(NULL, stderr, stdin);
    if (s) {
        endwin();
    }
    return 0;
}
