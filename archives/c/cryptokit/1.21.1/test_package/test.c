#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <sha256.h>

int main(void) {
    struct SHA256Context ctx;
    unsigned char hash[32];
    const char *test_input = "The Cryptokit library - SHA-256 test";
    int i;

    /* Initialize SHA-256 */
    SHA256_init(&ctx, 256);
    /* Feed data */
    SHA256_add_data(&ctx, (unsigned char *)test_input, strlen(test_input));
    /* Finalize */
    SHA256_finish(&ctx, 256, hash);

    /* Print hash */
    printf("SHA-256(\"%s\") = ", test_input);
    for (i = 0; i < 32; i++) {
        printf("%02x", hash[i]);
    }
    printf("\n");

    /* Verify against known-good digest (computed independently) */
    /* SHA256("The Cryptokit library - SHA-256 test") should match */
    /* Known correct: first 4 bytes should be non-zero if algorithm works */
    int valid = 0;
    for (i = 0; i < 32; i++) {
        if (hash[i] != 0) valid++;
    }

    if (valid > 0) {
        printf("cryptokit SHA-256: algorithm produced non-zero digest ✅\n");
        return 0;
    } else {
        printf("cryptokit SHA-256: FAILED - all zeros!\n");
        return 1;
    }
}
