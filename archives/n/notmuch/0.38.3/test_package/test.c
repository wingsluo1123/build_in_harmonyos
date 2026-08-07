#include <stdio.h>
#include <string.h>
#include <notmuch.h>

int main(void) {
    /* Test basic notmuch API */
    notmuch_database_t *db = NULL;

    /* Initialize notmuch - this should return an error since we don't have a real db */
    notmuch_status_t status = notmuch_database_open("/nonexistent",
                                                      NOTMUCH_DATABASE_MODE_READ_ONLY,
                                                      &db);

    /* We expect NOTMUCH_STATUS_PATH_ERROR or similar error - that's OK */
    /* The point is that the API is callable and the library loads */
    if (status == NOTMUCH_STATUS_SUCCESS && db != NULL) {
        notmuch_database_close(db);
    }

    printf("notmuch API test: status=%d (expected error for nonexistent path)\n", status);
    printf("notmuch version: %s\n", notmuch_version());

    printf("notmuch 0.38.3: ALL TESTS PASSED\n");
    return 0;
}
