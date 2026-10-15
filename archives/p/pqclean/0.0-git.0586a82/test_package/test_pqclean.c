/* Consumer test for pqclean: ML-KEM-768 encapsulation round-trip and
 * ML-DSA-65 sign/verify round-trip through the packaged static library. */
#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include "pqclean/ml-kem-768/api.h"
#include "pqclean/ml-dsa-65/api.h"

static int failures = 0;

#define CHECK(cond, name)                                      \
    do {                                                       \
        if (!(cond)) {                                         \
            printf("FAIL: %s\n", name);                        \
            failures++;                                        \
        } else {                                               \
            printf("ok: %s\n", name);                          \
        }                                                      \
    } while (0)

int main(void) {
    /* --- ML-KEM-768: keypair / enc / dec round-trip --- */
    uint8_t pk[PQCLEAN_MLKEM768_CLEAN_CRYPTO_PUBLICKEYBYTES];
    uint8_t sk[PQCLEAN_MLKEM768_CLEAN_CRYPTO_SECRETKEYBYTES];
    uint8_t ct[PQCLEAN_MLKEM768_CLEAN_CRYPTO_CIPHERTEXTBYTES];
    uint8_t ss_enc[PQCLEAN_MLKEM768_CLEAN_CRYPTO_BYTES];
    uint8_t ss_dec[PQCLEAN_MLKEM768_CLEAN_CRYPTO_BYTES];

    CHECK(0 == PQCLEAN_MLKEM768_CLEAN_crypto_kem_keypair(pk, sk),
          "ml-kem-768 keypair returns 0");
    CHECK(0 == PQCLEAN_MLKEM768_CLEAN_crypto_kem_enc(ct, ss_enc, pk),
          "ml-kem-768 enc returns 0");
    CHECK(0 == PQCLEAN_MLKEM768_CLEAN_crypto_kem_dec(ss_dec, ct, sk),
          "ml-kem-768 dec returns 0");
    CHECK(0 == memcmp(ss_enc, ss_dec, sizeof(ss_enc)),
          "ml-kem-768 shared secrets match");

    /* Tampered ciphertext must fail to decapsulate into the same secret. */
    ct[0] ^= 1;
    PQCLEAN_MLKEM768_CLEAN_crypto_kem_dec(ss_dec, ct, sk);
    CHECK(0 != memcmp(ss_enc, ss_dec, sizeof(ss_enc)),
          "ml-kem-768 tampered ct does not reproduce the shared secret");

    /* --- ML-DSA-65: keypair / signature / verify round-trip --- */
    uint8_t spk[PQCLEAN_MLDSA65_CLEAN_CRYPTO_PUBLICKEYBYTES];
    uint8_t ssk[PQCLEAN_MLDSA65_CLEAN_CRYPTO_SECRETKEYBYTES];
    uint8_t sig[PQCLEAN_MLDSA65_CLEAN_CRYPTO_BYTES];
    size_t siglen = 0;
    const uint8_t msg[] = "pqclean ohos consumer test message";
    size_t msglen = sizeof(msg) - 1;

    CHECK(0 == PQCLEAN_MLDSA65_CLEAN_crypto_sign_keypair(spk, ssk),
          "ml-dsa-65 keypair returns 0");
    CHECK(0 == PQCLEAN_MLDSA65_CLEAN_crypto_sign_signature(
                   sig, &siglen, msg, msglen, ssk),
          "ml-dsa-65 signature returns 0");
    CHECK(siglen > 0 && siglen <= PQCLEAN_MLDSA65_CLEAN_CRYPTO_BYTES,
          "ml-dsa-65 signature length within bounds");
    CHECK(0 == PQCLEAN_MLDSA65_CLEAN_crypto_sign_verify(
                   sig, siglen, msg, msglen, spk),
          "ml-dsa-65 verify accepts valid signature");

    /* Tampered message must fail verification. */
    uint8_t bad[sizeof(msg)];
    memcpy(bad, msg, sizeof(msg));
    bad[0] ^= 1;
    CHECK(0 != PQCLEAN_MLDSA65_CLEAN_crypto_sign_verify(
                    sig, siglen, bad, msglen, spk),
          "ml-dsa-65 verify rejects tampered message");

    if (failures == 0) {
        printf("pqclean 0.0-git.0586a82 OHOS test_package: all assertions passed\n");
        return 0;
    }
    printf("%d assertions failed\n", failures);
    return 1;
}
