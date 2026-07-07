#include <blake3.h>
#include <string.h>

int main() {
    uint8_t output[BLAKE3_OUT_LEN];
    blake3_hasher hasher;
    blake3_hasher_init(&hasher);
    blake3_hasher_update(&hasher, "abc", 3);
    blake3_hasher_finalize(&hasher, output, BLAKE3_OUT_LEN);
    return 0;
}
