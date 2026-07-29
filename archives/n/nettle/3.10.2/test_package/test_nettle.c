#include <stdio.h>
#include <string.h>

#include <gmp.h>
#include <nettle/nettle-meta.h>
#include <nettle/rsa.h>
#include <nettle/sha2.h>
#include <nettle/version.h>

static int check_sha256(void)
{
    static const unsigned char expected[SHA256_DIGEST_SIZE] = {
        0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
        0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
        0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
        0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad,
    };
    struct sha256_ctx ctx;
    unsigned char digest[SHA256_DIGEST_SIZE];

    sha256_init(&ctx);
    sha256_update(&ctx, 3, (const uint8_t *)"abc");
    sha256_digest(&ctx, SHA256_DIGEST_SIZE, digest);

    return memcmp(digest, expected, sizeof(expected)) == 0;
}

static int check_hogweed_gmp(void)
{
    struct rsa_public_key key;
    int ok;

    rsa_public_key_init(&key);
    mpz_set_ui(key.e, 65537);
    ok = mpz_cmp_ui(key.e, 65537) == 0;
    rsa_public_key_clear(&key);

    return ok;
}

int main(void)
{
    const struct nettle_hash *hash = nettle_lookup_hash("sha256");

    if (nettle_version_major() != NETTLE_VERSION_MAJOR ||
        nettle_version_minor() != NETTLE_VERSION_MINOR) {
        fprintf(stderr, "nettle runtime version does not match headers\n");
        return 1;
    }
    if (hash == NULL || hash->digest_size != SHA256_DIGEST_SIZE) {
        fprintf(stderr, "nettle_lookup_hash did not return sha256 metadata\n");
        return 1;
    }
    if (!check_sha256()) {
        fprintf(stderr, "sha256 digest check failed\n");
        return 1;
    }
    if (!check_hogweed_gmp()) {
        fprintf(stderr, "hogweed/GMP RSA key check failed\n");
        return 1;
    }

    return 0;
}
