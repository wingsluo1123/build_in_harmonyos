/*
 * HarmonyOS special test for libinfnoise 0.3.3.
 *
 * Distinct from the consumer test (test.c, which simulates an upper-layer
 * component linking the public API): this is a platform-contract test that
 * asserts the library's observable behaviour on the HarmonyOS PC (OHOS arm64)
 * target when the physical Infinite Noise USB TRNG device is absent:
 *
 *   A1. listUSBDevices() must return NULL and set *message (no device)
 *   A2. initInfnoise() must return false and set context.message (no device)
 *   A3. deinitInfnoise() must be safely callable and not crash
 *
 * All assertions are real observable behaviour of the installed library;
 * the test exits non-zero if any contract is violated (no fake output).
 */
#include <stdio.h>
#include <stdlib.h>
#include <libinfnoise.h>

static int failures = 0;

static void check(int cond, const char *name) {
    if (cond) {
        printf("PASS %s\n", name);
    } else {
        printf("FAIL %s\n", name);
        failures++;
    }
}

int main(void) {
    const char *message = NULL;

    /* A1: without the USB TRNG, listUSBDevices returns NULL and sets message */
    infnoise_devlist_node_t *devs = listUSBDevices(&message);
    check(devs == NULL, "A1 listUSBDevices NULL without device");
    check(message != NULL && message[0] != '\0',
          "A1b listUSBDevices sets non-empty *message");

    /* A2: initInfnoise fails cleanly without the device */
    struct infnoise_context ctx;
    message = NULL;
    ctx.message = NULL;
    int ok = initInfnoise(&ctx, NULL, true, false);
    check(ok == 0, "A2 initInfnoise returns false without device");
    check(ctx.message != NULL && ctx.message[0] != '\0',
          "A2b initInfnoise sets non-empty context.message");

    /* A3: deinitInfnoise is safely callable even after failed init */
    deinitInfnoise(&ctx);
    check(1, "A3 deinitInfnoise safe");

    if (failures == 0) {
        printf("harmony special test: ALL PASS (no-device contract)\n");
        return 0;
    }
    printf("harmony special test: %d assertion(s) FAILED\n", failures);
    return 1;
}
