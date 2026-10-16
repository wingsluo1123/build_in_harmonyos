/* test_package dependency functional test — OpenSSL (typst's only external
 * C dependency).
 *
 * typst-cli unconditionally enables typst-kit's `system-downloader` feature,
 * which links OpenSSL (openssl-sys).  The recipe links the conan `openssl`
 * package *statically*, so the packaged `typst` binary carries no runtime
 * DT_NEEDED entry for it — nothing about running typst alone proves the
 * dependency actually works on HarmonyOS PC.  This consumer program is
 * compiled against the same conan openssl package and exercises real OpenSSL
 * code paths:
 *   - OpenSSL_version() identifies the library
 *   - EVP SHA-256 digest of a known vector
 *   - EVP AES-256-GCM round trip (encrypt then decrypt)
 *   - RAND_bytes()
 * It exits non-zero if any assertion fails.
 */
#include <stdio.h>
#include <string.h>
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/crypto.h>

static int passed = 0, failed = 0;

static void check(const char *name, int cond) {
    if (cond) { passed++; printf("  [PASS] %s\n", name); }
    else      { failed++; printf("  [FAIL] %s\n", name); }
}

static void hex(const unsigned char *in, size_t n, char *out) {
    static const char *d = "0123456789abcdef";
    for (size_t i = 0; i < n; i++) { out[2*i] = d[in[i] >> 4]; out[2*i+1] = d[in[i] & 15]; }
    out[2*n] = 0;
}

int main(void) {
    printf("OpenSSL dependency functional test\n");
    printf("  OpenSSL_version: %s\n", OpenSSL_version(OPENSSL_VERSION));

    /* SHA-256("abc") = ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad */
    unsigned char md[EVP_MAX_MD_SIZE];
    unsigned int mdlen = 0;
    char mdhex[EVP_MAX_MD_SIZE * 2 + 1];
    EVP_MD_CTX *ctx = EVP_MD_CTX_new();
    EVP_DigestInit_ex(ctx, EVP_sha256(), NULL);
    EVP_DigestUpdate(ctx, "abc", 3);
    EVP_DigestFinal_ex(ctx, md, &mdlen);
    EVP_MD_CTX_free(ctx);
    hex(md, mdlen, mdhex);
    check("EVP SHA-256(\"abc\") matches known vector",
          strcmp(mdhex, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") == 0);

    /* AES-256-GCM round trip */
    unsigned char key[32], iv[12];
    check("RAND_bytes(key) succeeds", RAND_bytes(key, sizeof key) == 1);
    check("RAND_bytes(iv) succeeds", RAND_bytes(iv, sizeof iv) == 1);
    const unsigned char pt[] = "HarmonyOS PC + OpenSSL 3.x AES-GCM round trip";
    unsigned char ct[128], rt[128], tag[16];
    int len = 0;
    EVP_CIPHER_CTX *c = EVP_CIPHER_CTX_new();
    int ok_enc = EVP_EncryptInit_ex(c, EVP_aes_256_gcm(), NULL, key, iv) == 1
              && EVP_EncryptUpdate(c, ct, &len, pt, (int)sizeof pt) == 1
              && EVP_EncryptFinal_ex(c, ct + len, &len) == 1
              && EVP_CIPHER_CTX_ctrl(c, EVP_CTRL_GCM_GET_TAG, 16, tag) == 1;
    EVP_CIPHER_CTX_free(c);
    int ctlen = (int)sizeof pt;
    check("EVP AES-256-GCM encrypt", ok_enc);

    c = EVP_CIPHER_CTX_new();
    int rlen = 0;
    int ok_dec = EVP_DecryptInit_ex(c, EVP_aes_256_gcm(), NULL, key, iv) == 1
              && EVP_DecryptUpdate(c, rt, &rlen, ct, ctlen) == 1
              && EVP_CIPHER_CTX_ctrl(c, EVP_CTRL_GCM_SET_TAG, 16, tag) == 1
              && EVP_DecryptFinal_ex(c, rt + rlen, &rlen) == 1;
    EVP_CIPHER_CTX_free(c);
    check("EVP AES-256-GCM decrypt restores plaintext",
          ok_dec && memcmp(pt, rt, sizeof pt) == 0);

    printf("\nRESULT: %d passed, %d failed\n", passed, failed);
    return failed ? 1 : 0;
}
