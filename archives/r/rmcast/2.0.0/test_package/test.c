/* test_package consumer for rmcast 2.0.0.
 *
 * Validates the installed library through its public API without requiring
 * an IP multicast network:
 *   1. RM_getVersion returns a non-empty version string (proves the library
 *      loads and its global state initializes).
 *   2. RM_setOption/RM_getOption round-trips for scalar options (TTL,
 *      MAX_NAK, MICROSLEEP) — exercises the configuration table before any
 *      network activity.
 * No RM_initialize/RM_joinGroup here: those need a live multicast network
 * (documented skip, not a silent removal).
 */
#include <rmcast.h>

#include <stdio.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, msg)                                        \
    do {                                                        \
        if (cond) {                                             \
            printf("PASS: %s\n", msg);                          \
        } else {                                                \
            printf("FAIL: %s\n", msg);                          \
            failures++;                                         \
        }                                                       \
    } while (0)

int main(void)
{
    /* 1. Version string is non-empty. */
    char version[256];
    memset(version, 0, sizeof(version));
    RM_getVersion(version, (int)sizeof(version) - 1);
    CHECK(version[0] != '\0', "RM_getVersion returns a non-empty version string");

    /* 2. TTL option round-trip. RM_setOption passes scalar option values
     * directly as the void* argument (upstream rmcast.c casts it to int);
     * RM_getOption writes the current value through the out pointer. */
    int ttl = 0;
    RM_setOption(TTL, (void *)(long)5);
    RM_getOption(TTL, &ttl);
    CHECK(ttl == 5, "RM_setOption/RM_getOption round-trip for TTL");

    /* 3. Second scalar option (MAX_NAK) round-trip. */
    int max_nak = 0;
    RM_setOption(MAX_NAK, (void *)(long)42);
    RM_getOption(MAX_NAK, &max_nak);
    CHECK(max_nak == 42, "RM_setOption/RM_getOption round-trip for MAX_NAK");

    /* 4. MICROSLEEP option round-trip. */
    int microsleep = 0;
    RM_setOption(MICROSLEEP, (void *)(long)1000);
    RM_getOption(MICROSLEEP, &microsleep);
    CHECK(microsleep == 1000, "RM_setOption/RM_getOption round-trip for MICROSLEEP");

    if (failures > 0) {
        printf("%d assertion(s) FAILED\n", failures);
        return 1;
    }
    printf("all 4 assertions passed\n");
    return 0;
}
