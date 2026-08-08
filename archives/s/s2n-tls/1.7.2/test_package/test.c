#include <s2n.h>
#include <stdio.h>

int main(void) {
    /* Initialize the s2n-tls library */
    if (s2n_init() != 0) {
        fprintf(stderr, "s2n_init() failed: %s\n", s2n_strerror(s2n_errno, "EN"));
        return 1;
    }

    /* Verify libcrypto is linked and accessible */
    unsigned long openssl_version = s2n_get_openssl_version();
    if (openssl_version == 0) {
        fprintf(stderr, "s2n_get_openssl_version() returned 0\n");
        s2n_cleanup_final();
        return 1;
    }

    printf("s2n-tls initialized successfully, OpenSSL version: 0x%lx\n", openssl_version);

    /* Clean up */
    if (s2n_cleanup_final() != 0) {
        fprintf(stderr, "s2n_cleanup_final() failed\n");
        return 1;
    }

    printf("test_s2n: PASS\n");
    return 0;
}
