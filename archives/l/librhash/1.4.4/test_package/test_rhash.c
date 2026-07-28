/* test_package/test_rhash.c — librhash 1.4.4 L1 smoke test.
 * Compute MD5 and SHA256 hash of a string, verify the result. */
#include <stdio.h>
#include <string.h>
#include <rhash.h>

int main(void) {
    const char *data = "hello librhash 1.4.4";
    size_t len = strlen(data);
    char digest[32];
    char hex[65];
    int i;

    rhash_library_init();

    /* Compute MD5 */
    int rc = rhash_msg(RHASH_MD5, data, len, digest);
    if (rc != 0) {
        fprintf(stderr, "MD5 computation failed: %d\n", rc);
        return 1;
    }
    rhash_print_bytes(hex, digest, 16, RHPR_HEX);
    if (strlen(hex) != 32) {
        fprintf(stderr, "MD5 hex length wrong: %zu\n", strlen(hex));
        return 1;
    }
    printf("MD5: %s\n", hex);

    /* Compute SHA256 */
    rc = rhash_msg(RHASH_SHA256, data, len, digest);
    if (rc != 0) {
        fprintf(stderr, "SHA256 computation failed: %d\n", rc);
        return 1;
    }
    rhash_print_bytes(hex, digest, 32, RHPR_HEX);
    if (strlen(hex) != 64) {
        fprintf(stderr, "SHA256 hex length wrong: %zu\n", strlen(hex));
        return 1;
    }
    printf("SHA256: %s\n", hex);

    printf("librhash 1.4.4: MD5 + SHA256 computation OK\n");
    return 0;
}
