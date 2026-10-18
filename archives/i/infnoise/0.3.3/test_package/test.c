/*
 * Consumer test for libinfnoise — simulates an upper-layer business component
 * (e.g. a RNG-driven application) that consumes the library ONLY through its
 * public installed headers (libinfnoise.h) and exported public API.
 *
 * Public API exercised: listUSBDevices / initInfnoise / deinitInfnoise.
 * Observable result on a machine without the Infinite Noise USB TRNG:
 *   - listUSBDevices returns NULL and *message is set
 *   - initInfnoise returns false and context.message is set
 * The program compiles, links against the installed lib, calls the public API
 * and exits 0 (normal, well-defined error path handling).
 */
#include <stdio.h>
#include <stdlib.h>
#include <libinfnoise.h>

int main(void) {
    const char *message = NULL;

    printf("consumer: listUSBDevices() ...\n");
    infnoise_devlist_node_t *devs = listUSBDevices(&message);
    if (devs == NULL) {
        printf("consumer: no device found (message: %s)\n",
               message ? message : "(null)");
    } else {
        infnoise_devlist_node_t *n = devs;
        while (n != NULL) {
            printf("consumer: device manufacturer=%s desc=%s serial=%s\n",
                   n->manufacturer, n->description, n->serial);
            n = n->next;
        }
        /* free list — public list nodes are heap-allocated by libinfnoise */
        n = devs;
        while (n != NULL) {
            infnoise_devlist_node_t *next = n->next;
            free(n);
            n = next;
        }
    }

    printf("consumer: initInfnoise(NULL, keccak, !debug) ...\n");
    struct infnoise_context ctx;
    if (initInfnoise(&ctx, NULL, true, false)) {
        printf("consumer: initInfnoise OK\n");
        deinitInfnoise(&ctx);
    } else {
        printf("consumer: initInfnoise failed (message: %s)\n",
               ctx.message ? ctx.message : "(null)");
    }

    printf("consumer: done (exit 0)\n");
    return 0;
}
