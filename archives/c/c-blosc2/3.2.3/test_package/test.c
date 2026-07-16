/*
 * c-blosc2 test_package
 * Based on upstream examples/simple.c (BSD-3-Clause)
 * Compresses data, decompresses, and verifies roundtrip correctness.
 */
#include <stdio.h>
#include "blosc2.h"

#define SIZE 1000

int main(void) {
    int data[SIZE];
    int data_out[SIZE];
    int data_dest[SIZE];
    int isize = sizeof(data);
    int osize = sizeof(data_out);
    int csize, dsize;
    int i;

    blosc2_init();
    blosc2_set_nthreads(2);

    for (i = 0; i < SIZE; i++) {
        data[i] = i;
    }

    csize = blosc1_compress(5, BLOSC_BITSHUFFLE, sizeof(int),
                             isize, data, data_out, osize);
    if (csize <= 0) {
        printf("Compression failed. Error code: %d\n", csize);
        blosc2_destroy();
        return 1;
    }

    dsize = blosc1_decompress(data_out, data_dest, sizeof(data_dest));
    if (dsize < 0) {
        printf("Decompression error. Error code: %d\n", dsize);
        blosc2_destroy();
        return dsize;
    }

    for (i = 0; i < SIZE; i++) {
        if (data[i] != data_dest[i]) {
            printf("Decompressed data differs from original!\n");
            blosc2_destroy();
            return -1;
        }
    }

    printf("Successful roundtrip!\n");
    blosc2_destroy();
    return 0;
}
