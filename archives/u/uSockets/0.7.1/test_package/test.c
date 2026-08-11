#include <libusockets.h>
#include <stdio.h>

/* L1 test: verify uSockets static library links and core API symbols resolve.
 * Creates an event loop (exercises epoll init) then frees it. */
int main(void) {
    struct us_loop_t *loop = us_create_loop(NULL, NULL, NULL, NULL, 0);
    if (!loop) {
        fprintf(stderr, "FAIL: us_create_loop returned NULL\n");
        return 1;
    }
    us_loop_free(loop);
    printf("PASS: uSockets 0.7.1 — us_create_loop / us_loop_free OK\n");
    return 0;
}
