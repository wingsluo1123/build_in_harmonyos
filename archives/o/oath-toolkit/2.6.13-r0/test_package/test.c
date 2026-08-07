#include <stdio.h>
#include <liboath/oath.h>

int main(void) {
    /* Test liboath HOTP generation */
    char otp[8 + 1];
    const char *secret = "12345678901234567890";
    size_t secret_len = 20;
    int rc = oath_hotp_generate(
        secret,
        secret_len,
        0,                        /* moving factor (counter) */
        6,                        /* number of digits */
        false,                    /* add checksum? */
        OATH_HOTP_DYNAMIC_TRUNCATION,
        otp
    );
    if (rc != OATH_OK) {
        fprintf(stderr, "oath_hotp_generate failed: %s\n", oath_strerror(rc));
        return 1;
    }
    printf("HOTP: %s\n", otp);

    /* Test liboath TOTP generation */
    rc = oath_totp_generate(
        secret,
        secret_len,
        0,                        /* current time */
        OATH_TOTP_DEFAULT_TIME_STEP_SIZE,
        OATH_TOTP_DEFAULT_START_TIME,
        6,                        /* number of digits */
        otp
    );
    if (rc != OATH_OK) {
        fprintf(stderr, "oath_totp_generate failed: %s\n", oath_strerror(rc));
        return 1;
    }
    printf("TOTP: %s\n", otp);

    /* Verify library version */
    printf("oath_toolkit version: %s\n", oath_check_version(NULL));

    return 0;
}
