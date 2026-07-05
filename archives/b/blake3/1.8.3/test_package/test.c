#include <stdio.h>
#include <string.h>
#include "blake3.h"

int main(void) {
    const char *ver = blake3_version();
    printf("blake3 version: %s\n", ver);
    blake3_hasher hasher;
    blake3_hasher_init(&hasher);
    blake3_hasher_update(&hasher, "hello", 5);
    uint8_t out[BLAKE3_OUT_LEN];
    blake3_hasher_finalize(&hasher, out, sizeof(out));
    printf("hash: %02x%02x%02x%02x...\n", out[0], out[1], out[2], out[3]);
    return 0;
}
