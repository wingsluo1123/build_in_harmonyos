#include <stdio.h>
#include <string.h>
#include <bearssl.h>

/* Test: compute SHA-256 of a known string and verify the digest */
int main(void) {
    const char *msg = "abc";
    unsigned char digest[32];
    br_sha256_context ctx;

    br_sha256_init(&ctx);
    br_sha256_update(&ctx, msg, strlen(msg));
    br_sha256_out(&ctx, digest);

    /* SHA-256("abc") = ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad */
    const unsigned char expected[32] = {
        0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
        0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
        0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
        0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad
    };

    if (memcmp(digest, expected, 32) != 0) {
        printf("FAIL: SHA-256 mismatch\n");
        return 1;
    }

    printf("BearSSL SHA-256 test: OK\n");
    return 0;
}
