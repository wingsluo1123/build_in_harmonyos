#include <zyre.h>
#include <stdio.h>
#include <string.h>

int main (void)
{
    int failures = 0;

    // 1) Version macros report 2.0.1
    printf ("ZYRE version: %d.%d.%d\n",
            ZYRE_VERSION_MAJOR, ZYRE_VERSION_MINOR, ZYRE_VERSION_PATCH);
    if (ZYRE_VERSION_MAJOR != 2
    ||  ZYRE_VERSION_MINOR != 0
    ||  ZYRE_VERSION_PATCH != 1
    ||  ZYRE_VERSION != ZYRE_MAKE_VERSION (2, 0, 1)) {
        fprintf (stderr, "FAIL: unexpected ZYRE version macros\n");
        failures++;
    }

    // 2) zyre_version() agrees with the compile-time macros
    uint64_t version = zyre_version ();
    if ((version / 10000) % 100 != ZYRE_VERSION_MAJOR
    ||  (version / 100) % 100 != ZYRE_VERSION_MINOR
    ||  version % 100 != ZYRE_VERSION_PATCH) {
        fprintf (stderr, "FAIL: zyre_version() %lu disagrees with macros\n",
                 (unsigned long) version);
        failures++;
    }

    // 3) Node lifecycle smoke: create, name, header, destroy (no network)
    zyre_t *node = zyre_new ("flow-check");
    if (!node) {
        fprintf (stderr, "FAIL: zyre_new returned NULL\n");
        return 1;
    }
    if (!streq (zyre_name (node), "flow-check")) {
        fprintf (stderr, "FAIL: zyre_name mismatch\n");
        failures++;
    }
    if (!zyre_uuid (node) || strlen (zyre_uuid (node)) != 32) {
        fprintf (stderr, "FAIL: zyre_uuid not a 32-char UUID string\n");
        failures++;
    }
    zyre_set_header (node, "X-FLOW", "smoke");
    zyre_destroy (&node);
    if (node != NULL) {
        fprintf (stderr, "FAIL: zyre_destroy did not NULL the handle\n");
        failures++;
    }

    // 4) zmsg assembly consumed through the public API surface
    zmsg_t *msg = zmsg_new ();
    zmsg_addstr (msg, "zyre-payload");
    if (!msg || zmsg_size (msg) != 1) {
        fprintf (stderr, "FAIL: zmsg assembly failed\n");
        failures++;
    }
    else {
        char *part = zmsg_popstr (msg);
        if (!part || !streq (part, "zyre-payload")) {
            fprintf (stderr, "FAIL: zmsg payload mismatch\n");
            failures++;
        }
        freen (part);
    }
    zmsg_destroy (&msg);

    if (failures == 0)
        printf ("All tests passed!\n");
    return failures ? 1 : 0;
}
