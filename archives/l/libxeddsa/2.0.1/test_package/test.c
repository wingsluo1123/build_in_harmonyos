#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <xeddsa.h>

/* Consumer test: use the installed public headers and the static library
 * through normal link. Exercises real public APIs (xeddsa_init, seed-based
 * Ed25519 signing, verification) with an observable result. */
int main(void) {
    uint8_t seed[32] = {0};
    uint8_t pub[32];
    uint8_t check_pub[32];
    uint8_t sig[64];
    const uint8_t msg[] = "libxeddsa consumer test";
    uint8_t verify_seed[32] = {0};

    if (xeddsa_init() < 0) {
        fprintf(stderr, "xeddsa_init failed\n");
        return 1;
    }

    /* Seed-based public key derivation (public API): deterministic. */
    seed_to_ed25519_pub(pub, seed);
    seed_to_ed25519_pub(check_pub, seed);
    if (memcmp(pub, check_pub, 32) != 0) {
        fprintf(stderr, "seed derivation is not deterministic\n");
        return 2;
    }

    /* Seed-based signing + verification (public API). */
    ed25519_seed_sign(sig, seed, msg, sizeof(msg) - 1);
    if (ed25519_verify(sig, pub, msg, sizeof(msg) - 1) != 0) {
        fprintf(stderr, "signature verification failed\n");
        return 3;
    }

    /* Tampered message must fail verification. */
    verify_seed[0] = 1;
    if (ed25519_verify(sig, pub, verify_seed, sizeof(verify_seed) - 1) == 0) {
        fprintf(stderr, "tampered message accepted\n");
        return 4;
    }

    printf("libxeddsa consumer test: OK (version %u.%u.%u)\n",
           XEDDSA_VERSION_MAJOR, XEDDSA_VERSION_MINOR, XEDDSA_VERSION_REVISION);
    return 0;
}
