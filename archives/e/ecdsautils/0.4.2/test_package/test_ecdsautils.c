/*
 * ecdsautils 0.4.2 鸿蒙PC消费者测试 (test_package)
 *
 * 直接编译、链接并运行，覆盖两条公开 API 面：
 *   1. include/ecdsautil/sha256.h —— SHA256 / HMAC-SHA256 标准向量
 *   2. include/ecdsautil/ecdsa.h  —— 签名/验签往返 + 篡改检测 + 非法公钥
 *
 * 断言通过 exit 0 表达；任一断言失败打印原因并返回非 0。
 */
#include <ecdsautil/ecdsa.h>
#include <ecdsautil/sha256.h>

#include <libuecc/ecc.h>

#include <stdio.h>
#include <string.h>

static int failures = 0;
/* Real assertion counters, both maintained by CHECK() itself so the summary
 * line can never state a number that disagrees with the code below. */
static int pass = 0;

#define CHECK(cond, msg) do { \
    if (cond) { \
        pass++; \
    } else { \
        fprintf(stderr, "FAIL: %s\n", msg); \
        failures++; \
    } \
} while (0)

static void to_hex(char *out, const unsigned char *data, size_t len) {
    static const char *hex = "0123456789abcdef";
    for (size_t i = 0; i < len; i++) {
        out[2 * i] = hex[data[i] >> 4];
        out[2 * i + 1] = hex[data[i] & 0x0f];
    }
    out[2 * len] = '\0';
}

int main(void) {
    unsigned char digest[ECDSA_SHA256_HASH_SIZE];
    char hex[2 * ECDSA_SHA256_HASH_SIZE + 1];

    /* ---- 1. SHA256 known-answer tests (FIPS 180-4 / NIST vectors) ---- */
    ecdsa_sha256_context_t sc;

    ecdsa_sha256_init(&sc);
    ecdsa_sha256_update(&sc, "abc", 3);
    ecdsa_sha256_final(&sc, digest);
    to_hex(hex, digest, ECDSA_SHA256_HASH_SIZE);
    CHECK(strcmp(hex, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") == 0, "SHA256(\"abc\") != FIPS 180-4 vector");

    ecdsa_sha256_init(&sc);
    ecdsa_sha256_final(&sc, digest);
    to_hex(hex, digest, ECDSA_SHA256_HASH_SIZE);
    CHECK(strcmp(hex, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855") == 0, "SHA256(\"\") != e3b0c442... vector");

    /* ---- 2. HMAC-SHA256 known-answer test (RFC 4231 test case 1,
              key padded to the 32-byte HMAC key size ecdsautils requires) ---- */
    unsigned char key[ECDSA_HMAC_SHA256_KEY_SIZE];
    unsigned char mac[ECDSA_SHA256_HASH_SIZE];
    memset(key, 0x0b, sizeof(key));
    ecdsa_sha256_hmac(mac, key, "Hi There", 8);
    to_hex(hex, mac, ECDSA_SHA256_HASH_SIZE);
    CHECK(strcmp(hex, "198a607eb44bfbc69903a0f1cf2bbdc5ba0aa3f3d9ae3c1c7a3b1696a0b68cf7") == 0, "HMAC-SHA256(\"Hi There\", 0x0b*32) mismatch");

    /* ---- 3. ECDSA sign / verify round trip on the legacy representation ---- */
    ecc_int256_t secret, hash, pub_packed;
    ecc_25519_work_t pubkey;
    ecdsa_signature_t sig;
    ecdsa_verify_context_t ctx;

    memset(secret.p, 0x11, sizeof(secret.p));
    ecc_25519_gf_sanitize_secret(&secret, &secret);

    ecc_25519_scalarmult_base(&pubkey, &secret);
    ecc_25519_store_packed_legacy(&pub_packed, &pubkey);

    CHECK(ecc_25519_load_packed_legacy(&pubkey, &pub_packed) == 1,
          "ecc_25519_load_packed_legacy rejected its own packed output");
    CHECK(ecdsa_is_valid_pubkey(&pubkey), "derived public key is not a valid ECDSA public key");

    ecdsa_sha256_init(&sc);
    ecdsa_sha256_update(&sc, "ecdsautils consumer test", 24);
    ecdsa_sha256_final(&sc, hash.p);

    ecdsa_sign_legacy(&sig, &hash, &secret);
    ecdsa_verify_prepare_legacy(&ctx, &hash, &sig);
    CHECK(ecdsa_verify_legacy(&ctx, &pubkey), "valid signature failed verification");
    CHECK(ecdsa_verify_list_legacy(&ctx, 1, &pubkey, 1) == 1,
          "ecdsa_verify_list_legacy did not count the valid signature");

    /* ---- 4. Tampered signature must be rejected ---- */
    sig.r.p[0] ^= 0x01;
    ecdsa_verify_prepare_legacy(&ctx, &hash, &sig);
    CHECK(!ecdsa_verify_legacy(&ctx, &pubkey), "tampered signature was accepted");
    sig.r.p[0] ^= 0x01;

    /* ---- 5. Signature over a different hash must be rejected ---- */
    ecdsa_sha256_init(&sc);
    ecdsa_sha256_update(&sc, "ecdsautils consumer test!", 25);
    ecdsa_sha256_final(&sc, hash.p);
    ecdsa_verify_prepare_legacy(&ctx, &hash, &sig);
    CHECK(!ecdsa_verify_legacy(&ctx, &pubkey), "signature over another hash was accepted");

    if (failures) {
        fprintf(stderr, "test_ecdsautils: %d/%d assertion(s) failed\n",
                failures, pass + failures);
        return 1;
    }
    /* pass/fail counts come from CHECK() itself, never a literal. */
    printf("test_ecdsautils: %d/%d assertions passed\n", pass, pass + failures);
    return 0;
}
