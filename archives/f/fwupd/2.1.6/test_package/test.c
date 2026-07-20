/*
 * test_package for fwupd 2.1.6
 * R34: Must call actual fwupd API, not just print strings
 */
#include <fwupd.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* R34: Call actual fwupd library API — get compiled version string */
    const gchar *version = fwupd_version_string();
    if (version == NULL) {
        fprintf(stderr, "FAIL: fwupd_version_string() returned NULL\n");
        return 1;
    }
    printf("fwupd version: %s\n", version);

    /* Also verify the runtime client can be created (no D-Bus needed for object) */
    FwupdClient *client = fwupd_client_new();
    if (client == NULL) {
        fprintf(stderr, "FAIL: fwupd_client_new() returned NULL\n");
        return 1;
    }
    g_object_unref(client);

    printf("test_package for fwupd %s: PASSED\n", version);
    return 0;
}
