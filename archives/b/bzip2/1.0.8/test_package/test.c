#include <stdio.h>
#include <string.h>
#include <bzlib.h>

int main(void) {
    /* Compress data using bzip2 library API */
    char input[] = "Hello, bzip2! This is a test of the bzip2 compression library.";
    char output[256];
    char decompressed[256];
    unsigned int input_len = strlen(input);
    unsigned int output_len = sizeof(output);
    unsigned int decompressed_len = sizeof(decompressed);
    int ret;

    /* Compress */
    ret = BZ2_bzBuffToBuffCompress(output, &output_len, input, input_len, 9, 0, 0);
    if (ret != BZ_OK) {
        printf("Compression failed with code %d\n", ret);
        return 1;
    }
    printf("Compressed %u bytes to %u bytes\n", input_len, output_len);

    /* Decompress */
    ret = BZ2_bzBuffToBuffDecompress(decompressed, &decompressed_len, output, output_len, 0, 0);
    if (ret != BZ_OK) {
        printf("Decompression failed with code %d\n", ret);
        return 1;
    }
    printf("Decompressed to %u bytes\n", decompressed_len);

    /* Verify round-trip */
    if (decompressed_len == input_len && memcmp(input, decompressed, input_len) == 0) {
        printf("test bzip2 1.0.8: OK - round-trip compression/decompression verified\n");
        return 0;
    } else {
        printf("Round-trip verification failed!\n");
        return 1;
    }
}
