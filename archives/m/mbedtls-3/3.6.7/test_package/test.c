#include <stdio.h>
#include <string.h>

#include <mbedtls/aes.h>
#include <mbedtls/sha256.h>
#include <mbedtls/version.h>

/* aesce.c 里的运行时探测缓存。探测函数在第一次 AES 运算时调用 getauxval。 */
extern signed char mbedtls_aesce_has_support_result;

static int expect_mem(const char *name, const unsigned char *got,
                      const unsigned char *want, size_t n)
{
    if (memcmp(got, want, n) == 0) {
        printf("PASS %s\n", name);
        return 0;
    }
    printf("FAIL %s\n", name);
    return 1;
}

int main(void)
{
    int failed = 0;
    char version[32];
    unsigned int number = mbedtls_version_get_number();

    mbedtls_version_get_string_full(version);
    printf("version_full=%s\n", version);
    printf("version_number=0x%08x\n", number);
    if (strstr(version, "3.6.7") == NULL) {
        printf("FAIL version string\n");
        failed++;
    } else {
        printf("PASS version string\n");
    }
    if (number != 0x03060700u) {
        printf("FAIL version number\n");
        failed++;
    } else {
        printf("PASS version number\n");
    }

    /* NIST AES-128-ECB, FIPS-197 C.1 */
    const unsigned char key[16] = {
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
        0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f
    };
    const unsigned char plain[16] = {
        0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
        0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff
    };
    const unsigned char cipher_want[16] = {
        0x69, 0xc4, 0xe0, 0xd8, 0x6a, 0x7b, 0x04, 0x30,
        0xd8, 0xcd, 0xb7, 0x80, 0x70, 0xb4, 0xc5, 0x5a
    };
    unsigned char cipher[16];
    unsigned char roundtrip[16];
    mbedtls_aes_context aes;
    mbedtls_aes_init(&aes);
    if (mbedtls_aes_setkey_enc(&aes, key, 128) != 0 ||
        mbedtls_aes_crypt_ecb(&aes, MBEDTLS_AES_ENCRYPT, plain, cipher) != 0) {
        printf("FAIL aes encrypt call\n");
        failed++;
    } else {
        failed += expect_mem("aes-128-ecb", cipher, cipher_want, 16);
    }
    printf("aesce_has_support_result=%d\n", (int) mbedtls_aesce_has_support_result);
    if (mbedtls_aesce_has_support_result != 1) {
        printf("FAIL aesce runtime probe (want 1 = HWCAP AES+ASIMD)\n");
        failed++;
    } else {
        printf("PASS aesce runtime probe\n");
    }
    mbedtls_aes_free(&aes);

    mbedtls_aes_init(&aes);
    if (mbedtls_aes_setkey_dec(&aes, key, 128) != 0 ||
        mbedtls_aes_crypt_ecb(&aes, MBEDTLS_AES_DECRYPT, cipher, roundtrip) != 0) {
        printf("FAIL aes decrypt call\n");
        failed++;
    } else {
        failed += expect_mem("aes-128-ecb-roundtrip", roundtrip, plain, 16);
    }
    mbedtls_aes_free(&aes);

    /* SHA-256("abc") */
    const unsigned char abc[] = "abc";
    unsigned char digest[32];
    const unsigned char sha_want[32] = {
        0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
        0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
        0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
        0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad
    };
    if (mbedtls_sha256(abc, 3, digest, 0) != 0) {
        printf("FAIL sha256 call\n");
        failed++;
    } else {
        failed += expect_mem("sha256-abc", digest, sha_want, 32);
    }

    printf("consumer_failed=%d\n", failed);
    return failed == 0 ? 0 : 1;
}
