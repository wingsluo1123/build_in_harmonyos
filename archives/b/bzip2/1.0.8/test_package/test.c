#include <stdio.h>
#include <string.h>
#include <bzlib.h>

int main(void) {
    char input[] = "Hello, bzip2 on HarmonyOS! This is a test of the bzip2 library. "
                   "The quick brown fox jumps over the lazy dog. "
                   "bzip2 uses the Burrows-Wheeler block sorting text compression algorithm "
                   "and Huffman coding to achieve high compression ratios.";
    char compressed[4096];
    char decompressed[4096];
    unsigned int compressed_len = sizeof(compressed);
    unsigned int decompressed_len = sizeof(decompressed);
    int ret;

    /* Compress */
    ret = BZ2_bzBuffToBuffCompress(compressed, &compressed_len,
                                   input, strlen(input) + 1,
                                   1, 0, 0);
    if (ret != BZ_OK) {
        printf("Compression failed with error %d\n", ret);
        return 1;
    }
    printf("Compressed %zu bytes to %u bytes\n", strlen(input) + 1, compressed_len);

    /* Decompress */
    ret = BZ2_bzBuffToBuffDecompress(decompressed, &decompressed_len,
                                    compressed, compressed_len, 0, 0);
    if (ret != BZ_OK) {
        printf("Decompression failed with error %d\n", ret);
        return 1;
    }

    /* Verify round-trip */
    if (strcmp(input, decompressed) == 0) {
        printf("bzip2 library test: PASS (version: %s)\n", BZ2_bzlibVersion());
        return 0;
    } else {
        printf("bzip2 library test: FAIL (data mismatch)\n");
        return 1;
    }
}
