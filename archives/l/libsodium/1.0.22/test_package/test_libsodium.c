/* test_package/test_libsodium.c — functional smoke test for libsodium.
 * Calls sodium_init() and checks the library version string.
 */
#include <sodium.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    if (sodium_init() < 0) {
        fprintf(stderr, "FAIL: sodium_init() returned -1\n");
        return 1;
    }
    printf("PASS: sodium_init() OK\n");

    const char *ver = sodium_version_string();
    if (ver == NULL || strlen(ver) == 0) {
        fprintf(stderr, "FAIL: sodium_version_string() returned empty\n");
        return 1;
    }
    printf("PASS: libsodium version = %s\n", ver);

    int major = sodium_library_version_major();
    if (major <= 0) {
        fprintf(stderr, "FAIL: sodium_library_version_major() = %d\n", major);
        return 1;
    }
    printf("PASS: libsodium major = %d\n", major);

    printf("All tests passed.\n");
    return 0;
}
