/* librnd test_package: base64 codec roundtrip via real librnd-core API.
 * Mirrors upstream tests/base64/main.c vectors plus explicit known-answer
 * checks. 6 checks total; each failure prints to stderr and flips rc.
 */
#include <stdio.h>
#include <string.h>

#include <librnd/core/base64.h>

static int check_roundtrip(const char *label, const char *str)
{
    size_t ilen = strlen(str);
    char bin[512];
    unsigned char plain[256];
    size_t len, olen;

    memset(plain, '#', sizeof(plain));
    len = rnd_base64_bin2str(bin, sizeof(bin), (const unsigned char *)str, ilen);
    if (len == 0 && ilen != 0) {
        fprintf(stderr, "FAIL %s: encode returned 0\n", label);
        return 1;
    }
    bin[len] = '\0';
    olen = rnd_base64_str2bin(plain, sizeof(plain), bin, len);
    plain[olen] = '\0';
    if (strcmp((const char *)plain, str) != 0 || ilen != olen) {
        fprintf(stderr, "FAIL %s: roundtrip mismatch ('%s' -> '%s')\n", label, str, bin);
        return 1;
    }
    printf("PASS %s: '%s' -> '%s' (%lu bytes)\n", label, str, bin, (unsigned long)len);
    return 0;
}

int main(void)
{
    int rc = 0;
    char bin[64];
    unsigned char plain[64];
    size_t len, olen;

    /* check 1: known-answer encode of "Man" (RFC 4648 vector) */
    len = rnd_base64_bin2str(bin, sizeof(bin), (const unsigned char *)"Man", 3);
    bin[len] = '\0';
    if (len != 4 || strcmp(bin, "TWFu") != 0) {
        fprintf(stderr, "FAIL known-encode: got '%s'/%lu, want 'TWFu'/4\n", bin, (unsigned long)len);
        rc |= 1;
    }
    else {
        printf("PASS known-encode: 'Man' -> 'TWFu'\n");
    }

    /* check 2: known-answer decode of "TWFu" */
    olen = rnd_base64_str2bin(plain, sizeof(plain), "TWFu", 4);
    plain[olen] = '\0';
    if (olen != 3 || strcmp((const char *)plain, "Man") != 0) {
        fprintf(stderr, "FAIL known-decode: got '%s'/%lu, want 'Man'/3\n", plain, (unsigned long)olen);
        rc |= 1;
    }
    else {
        printf("PASS known-decode: 'TWFu' -> 'Man'\n");
    }

    /* checks 3-6: roundtrips (upstream vectors + OHOS-flavored payload) */
    rc |= check_roundtrip("roundtrip-wiki", "any carnal pleasure.");
    rc |= check_roundtrip("roundtrip-plain", "any carnal pleasure");
    rc |= check_roundtrip("roundtrip-short", "Man");
    rc |= check_roundtrip("roundtrip-ohos", "Hello, HarmonyOS PC!");

    if (rc == 0)
        printf("librnd base64: all 6 checks OK\n");
    else
        fprintf(stderr, "librnd base64: %d check(s) FAILED\n", rc);
    return rc;
}
