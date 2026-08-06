#include <stdio.h>
#include <stdlib.h>
#include <archive.h>
#include <archive_entry.h>

int main(void) {
    struct archive *a = archive_write_new();
    if (a == NULL) {
        fprintf(stderr, "Failed to create archive handle\n");
        return 1;
    }
    int r = archive_write_free(a);
    if (r != ARCHIVE_OK) {
        fprintf(stderr, "Failed to free archive handle: %s\n", archive_error_string(a));
        return 1;
    }
    printf("libarchive version: %s\n", archive_version_string());
    printf("test libarchive 3.8.7: OK\n");
    return 0;
}
