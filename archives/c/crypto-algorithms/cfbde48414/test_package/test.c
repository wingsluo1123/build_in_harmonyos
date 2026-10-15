#include <stdio.h>
#include <string.h>
#include "sha256.h"

/* Consumer test: compute SHA-256("abc") via the installed package headers,
 * and compile the packaged sha256.c implementation (source redistribution).
 * Expected digest matches the upstream known-answer vector. */
static const unsigned char expected[SHA256_BLOCK_SIZE] = {
    0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
    0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
    0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
    0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad
};

int main(void) {
    unsigned char buf[SHA256_BLOCK_SIZE];
    SHA256_CTX ctx;
    const unsigned char text[] = "abc";

    sha256_init(&ctx);
    sha256_update(&ctx, text, 3);
    sha256_final(&ctx, buf);

    if (memcmp(buf, expected, SHA256_BLOCK_SIZE) != 0) {
        printf("test_crypto-algorithms: FAILED\n");
        return 1;
    }
    printf("test_crypto-algorithms: PASSED\n");
    return 0;
}
