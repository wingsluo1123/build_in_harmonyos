#include <stdio.h>
#include <string.h>
#include "libkeccak.h"

int main(void) {
    struct libkeccak_state state;
    struct libkeccak_spec spec;
    unsigned char hashsum[32];

    /* SHA3-256 spec: bitrate=1088, capacity=512, output=256 */
    libkeccak_spec_sha3(&spec, 256);

    if (libkeccak_state_initialise(&state, &spec) != 0) {
        fprintf(stderr, "ERROR: libkeccak_state_initialise failed\n");
        return 1;
    }

    /* Hash empty string */
    if (libkeccak_digest(&state, "", 0, 0, LIBKECCAK_SHA3_SUFFIX, hashsum) != 0) {
        fprintf(stderr, "ERROR: libkeccak_digest failed\n");
        return 1;
    }

    /* Verify output is not all zeros */
    int all_zero = 1;
    for (int i = 0; i < 32; i++) {
        if (hashsum[i] != 0) {
            all_zero = 0;
            break;
        }
    }
    if (all_zero) {
        fprintf(stderr, "ERROR: hashsum is all zeros\n");
        return 1;
    }

    libkeccak_state_fast_destroy(&state);

    printf("SHA3-256(\"\") = ");
    for (int i = 0; i < 32; i++) {
        printf("%02x", hashsum[i]);
    }
    printf("\n");
    printf("test libkeccak 1.4.3: OK\n");
    return 0;
}
