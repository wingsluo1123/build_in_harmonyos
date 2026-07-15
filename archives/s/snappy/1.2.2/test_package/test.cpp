#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "snappy-c.h"

int main(void) {
    const char input[] = "Hello, Snappy! This is a compression test for OpenHarmony.";
    size_t input_len = strlen(input);

    /* Compress */
    size_t compressed_len = snappy_max_compressed_length(input_len);
    char *compressed = (char *)malloc(compressed_len);
    if (!compressed) {
        fprintf(stderr, "malloc failed\n");
        return 1;
    }
    snappy_status rc = snappy_compress(input, input_len, compressed, &compressed_len);
    if (rc != SNAPPY_OK) {
        fprintf(stderr, "snappy_compress failed: %d\n", rc);
        free(compressed);
        return 1;
    }

    /* Decompress */
    size_t uncompressed_len = input_len;
    char *uncompressed = (char *)malloc(uncompressed_len + 1);
    if (!uncompressed) {
        fprintf(stderr, "malloc failed\n");
        free(compressed);
        return 1;
    }
    rc = snappy_uncompress(compressed, compressed_len, uncompressed, &uncompressed_len);
    if (rc != SNAPPY_OK) {
        fprintf(stderr, "snappy_uncompress failed: %d\n", rc);
        free(compressed);
        free(uncompressed);
        return 1;
    }
    uncompressed[uncompressed_len] = '\0';

    /* Verify round-trip */
    if (uncompressed_len != input_len || memcmp(uncompressed, input, input_len) != 0) {
        fprintf(stderr, "Round-trip mismatch!\n");
        free(compressed);
        free(uncompressed);
        return 1;
    }

    printf("snappy compress/decompress round-trip: OK (input=%zu, compressed=%zu)\n",
           input_len, compressed_len);

    free(compressed);
    free(uncompressed);
    return 0;
}
