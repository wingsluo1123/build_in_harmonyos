/* Consumer test for libvdeplug 4.0.1 on HarmonyOS PC (aarch64).
 *
 * Exercises the real library API end to end:
 *  1. vde_open("null://")  -> dlopens lib/vdeplug/libvdeplug_null.so plugin
 *  2. vde_send()           -> frame accepted by the null plugin
 *  3. vde_datafd()/vde_ctlfd() -> valid descriptors
 *  4. vde_close()
 *  5. negative case: unknown VNL scheme must fail (NULL conn)
 */
#include <libvdeplug.h>
#include <stdio.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, msg)                                                   \
    do {                                                                   \
        if (cond) {                                                        \
            printf("PASS: %s\n", (msg));                                   \
        } else {                                                           \
            printf("FAIL: %s\n", (msg));                                   \
            failures++;                                                    \
        }                                                                  \
    } while (0)

int main(void) {
    struct vde_open_args open_args = {0, NULL, 0};
    unsigned char frame[64];
    ssize_t sent;

    /* 1. open the null:// plugin (plugin dlopen path via dladdr) */
    VDECONN *conn = vde_open((char *)"null://", (char *)"consumer-test",
                             &open_args);
    CHECK(conn != NULL, "vde_open(null://) returns a connection");

    if (conn) {
        /* 2. send an Ethernet frame (null plugin discards it) */
        memset(frame, 0x42, sizeof(frame));
        sent = vde_send(conn, frame, sizeof(frame), 0);
        CHECK(sent == (ssize_t)sizeof(frame),
              "vde_send() accepts a full frame");

        /* 3. descriptors: datafd valid; null:// has no control socket and
         *    libvdeplug_null.c returns -1 for ctlfd by design */
        CHECK(vde_datafd(conn) >= 0, "vde_datafd() is a valid fd");
        CHECK(vde_ctlfd(conn) == -1,
              "vde_ctlfd() is -1 for null:// (no control socket by design)");

        /* 4. clean close */
        CHECK(vde_close(conn) == 0, "vde_close() returns 0");
    }

    /* 5. negative: unknown scheme must not open */
    VDECONN *bad = vde_open((char *)"definitely-not-a-plugin://",
                            (char *)"consumer-test", &open_args);
    CHECK(bad == NULL, "vde_open(unknown scheme) fails as expected");
    if (bad) {
        vde_close(bad);
    }

    printf("libvdeplug 4.0.1 consumer test: %s\n",
           failures == 0 ? "OK" : "FAILED");
    return failures == 0 ? 0 : 1;
}
