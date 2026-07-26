/* OpenSSL 1.1.1w consumer test: exercise the packaged API and libraries. */
#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <openssl/opensslv.h>
#include <openssl/sha.h>
#include <openssl/ssl.h>
#include <stdio.h>
#include <string.h>

static int test_version(void) {
    const char *version = OpenSSL_version(OPENSSL_VERSION);
    if (version && strstr(version, "1.1.1w") != NULL) {
        printf("[PASS] OpenSSL version: %s\n", version);
        return 1;
    }
    printf("[FAIL] OpenSSL version mismatch: %s\n", version ? version : "NULL");
    return 0;
}

static int test_sha256(void) {
    static const unsigned char expected[SHA256_DIGEST_LENGTH] = {
        0x92, 0x16, 0x89, 0x6d, 0x02, 0xa0, 0xf6, 0xce,
        0x8d, 0x4c, 0xb2, 0x0c, 0xc5, 0x5d, 0x5e, 0xb7,
        0xf5, 0x55, 0xd3, 0x0d, 0x01, 0x7e, 0x0a, 0x42,
        0xd2, 0x9a, 0x09, 0x53, 0x8c, 0x8c, 0xed, 0xbc
    };
    const char *message = "Hello, OpenSSL 1.1.1w!";
    unsigned char digest[SHA256_DIGEST_LENGTH];

    SHA256((const unsigned char *)message, strlen(message), digest);
    if (memcmp(digest, expected, sizeof(expected)) == 0) {
        printf("[PASS] SHA-256 digest matches\n");
        return 1;
    }
    printf("[FAIL] SHA-256 digest mismatch\n");
    return 0;
}

static int test_ssl_context(void) {
    SSL_CTX *ctx;

    SSL_library_init();
    SSL_load_error_strings();
    ctx = SSL_CTX_new(TLS_method());
    if (ctx != NULL) {
        SSL_CTX_free(ctx);
        printf("[PASS] SSL_CTX created successfully\n");
        return 1;
    }
    printf("[FAIL] SSL_CTX creation failed\n");
    return 0;
}

static int test_aes_round_trip(void) {
    static const unsigned char key[32] = {0};
    static const unsigned char iv[16] = {0};
    static const unsigned char plaintext[] = "OpenSSL Conan OHOS test";
    unsigned char ciphertext[64];
    unsigned char recovered[64];
    int ciphertext_length = 0;
    int final_length = 0;
    int recovered_length = 0;
    int recovered_final_length = 0;
    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();

    if (ctx == NULL ||
        EVP_EncryptInit_ex(ctx, EVP_aes_256_cbc(), NULL, key, iv) != 1 ||
        EVP_EncryptUpdate(ctx, ciphertext, &ciphertext_length, plaintext,
                          (int)strlen((const char *)plaintext)) != 1 ||
        EVP_EncryptFinal_ex(ctx, ciphertext + ciphertext_length, &final_length) != 1) {
        EVP_CIPHER_CTX_free(ctx);
        printf("[FAIL] AES encryption failed\n");
        return 0;
    }
    ciphertext_length += final_length;
    EVP_CIPHER_CTX_reset(ctx);
    if (EVP_DecryptInit_ex(ctx, EVP_aes_256_cbc(), NULL, key, iv) != 1 ||
        EVP_DecryptUpdate(ctx, recovered, &recovered_length, ciphertext,
                          ciphertext_length) != 1 ||
        EVP_DecryptFinal_ex(ctx, recovered + recovered_length,
                            &recovered_final_length) != 1) {
        EVP_CIPHER_CTX_free(ctx);
        printf("[FAIL] AES decryption failed\n");
        return 0;
    }
    recovered_length += recovered_final_length;
    EVP_CIPHER_CTX_free(ctx);
    if (recovered_length == (int)strlen((const char *)plaintext) &&
        memcmp(recovered, plaintext, (size_t)recovered_length) == 0) {
        printf("[PASS] AES-256-CBC round-trip succeeded\n");
        return 1;
    }
    printf("[FAIL] AES round-trip mismatch\n");
    return 0;
}

int main(void) {
    int passed = 0;
    const int total = 4;

    passed += test_version();
    passed += test_sha256();
    passed += test_ssl_context();
    passed += test_aes_round_trip();
    printf("Results: %d/%d tests passed\n", passed, total);
    return passed == total ? 0 : 1;
}
