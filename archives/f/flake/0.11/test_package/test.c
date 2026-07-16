#include <stdio.h>
#include <string.h>
#include <flake.h>

int main(void) {
    /* Verify FLAKE_IDENT contains the library identifier string */
    if (strstr(FLAKE_IDENT, "Flake") == NULL) {
        fprintf(stderr, "FLAKE_IDENT mismatch: %s\n", FLAKE_IDENT);
        return 1;
    }

    /* Test flake_set_defaults — initializes encoding parameters from compression level */
    FlakeEncodeParams params;
    params.compression = 5;
    int ret = flake_set_defaults(&params);
    if (ret != 0) {
        fprintf(stderr, "flake_set_defaults failed: %d\n", ret);
        return 1;
    }

    /* Verify defaults were actually set (block_time_ms should be non-zero after init) */
    if (params.block_time_ms <= 0) {
        fprintf(stderr, "flake_set_defaults did not set block_time_ms\n");
        return 1;
    }

    printf("flake API test passed: %s, block_time_ms=%d\n", FLAKE_IDENT, params.block_time_ms);
    return 0;
}
