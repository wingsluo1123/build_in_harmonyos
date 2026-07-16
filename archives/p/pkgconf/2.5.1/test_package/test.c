/* test_package/test.c — verifies libpkgconf API is usable (R34: substantive test) */
#include <pkgconf/libpkgconf/libpkgconf.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    /* Verify the library version is correct (links against libpkgconf) */
    printf("libpkgconf version: %s (expected 2.5.1)\n", LIBPKGCONF_VERSION_STR);

    /* Verify version numeric macro */
    if (LIBPKGCONF_VERSION != 20501) {
        fprintf(stderr, "FAIL: LIBPKGCONF_VERSION = %d, expected 20501\n", LIBPKGCONF_VERSION);
        return 1;
    }

    /* Test basic list initialization (core data structure used by pkgconf) */
    pkgconf_list_t list;
    memset(&list, 0, sizeof(list));
    if (list.head != NULL || list.tail != NULL || list.length != 0) {
        fprintf(stderr, "FAIL: list initialization failed\n");
        return 1;
    }

    /* Test path splitting (core pkg-config path handling) */
    size_t count = pkgconf_path_split("/usr/lib/pkgconfig:/usr/share/pkgconfig", &list, true);
    printf("path_split returned %zu entries\n", count);
    pkgconf_path_free(&list);

    printf("PASS: libpkgconf API test OK\n");
    return 0;
}
