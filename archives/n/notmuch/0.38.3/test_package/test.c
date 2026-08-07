#include <stdio.h>
#include <string.h>
#include <notmuch.h>

int main(void) {
    /* Test basic notmuch API - exit code depends on API results (R34) */

    /* Test 1: notmuch_version() must return non-NULL */
    const char *version = notmuch_version();
    if (!version) {
        fprintf(stderr, "FAIL: notmuch_version() returned NULL\n");
        return 1;
    }
    printf("notmuch version: %s\n", version);

    /* Test 2: notmuch_database_open should fail for nonexistent path */
    notmuch_database_t *db = NULL;
    notmuch_status_t status = notmuch_database_open("/nonexistent",
                                                      NOTMUCH_DATABASE_MODE_READ_ONLY,
                                                      &db);
    /* We expect an error (not SUCCESS) since the path doesn't exist */
    if (status == NOTMUCH_STATUS_SUCCESS) {
        if (db) notmuch_database_close(db);
        fprintf(stderr, "FAIL: notmuch_database_open succeeded for nonexistent path\n");
        return 1;
    }

    printf("notmuch_database_open returned status %d (expected error)\n", status);
    printf("notmuch 0.38.3: ALL TESTS PASSED\n");
    return 0;
}
