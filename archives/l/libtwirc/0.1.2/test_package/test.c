#include <stdio.h>
#include <string.h>

#include "libtwirc.h"

/* Consumer smoke test: exercise the public API without network I/O.
 * twirc_init() must return a usable state, twirc_get_last_error() must be
 * TWIRC_ERR_NONE after a fresh state (before any socket operation), and
 * twirc_kill() must free the state cleanly. */
int main(void) {
    twirc_state_t *s = twirc_init();
    if (!s) {
        fprintf(stderr, "FAIL: twirc_init() returned NULL\n");
        return 1;
    }
    int err = twirc_get_last_error(s);
    if (err != TWIRC_ERR_NONE) {
        fprintf(stderr, "FAIL: fresh state last_error=%d (expected %d)\n",
                err, TWIRC_ERR_NONE);
        twirc_kill(s);
        return 2;
    }
    if (twirc_is_connected(s) != 0) {
        fprintf(stderr, "FAIL: fresh state must not be connected\n");
        twirc_kill(s);
        return 3;
    }
    twirc_kill(s);
    printf("libtwirc 0.1.2 consumer smoke: OK (init/none/not-connected/kill)\n");
    return 0;
}