/* Test for lzlib - compress and decompress data using lzlib API */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <limits.h>

#include "lzlib.h"

static int min_int(int x, int y) { return x <= y ? x : y; }

int main(void) {
    /* Test data to compress */
    const char *test_data = "Hello, lzlib! This is a test message for compression and decompression. "
                            "LZMA compression should handle this data correctly.";
    long insize = (long)strlen(test_data);

    /* Compress */
    LZ_Encoder *encoder = LZ_compress_open(1 << 20, 16, INT64_MAX);
    if (!encoder || LZ_compress_errno(encoder) != LZ_ok) {
        fprintf(stderr, "FAIL: LZ_compress_open failed\n");
        LZ_compress_close(encoder);
        return 1;
    }

    uint8_t compressed[4096];
    long comp_pos = 0;
    long inpos = 0;
    int finish_called = 0;

    while (LZ_compress_finished(encoder) != 1) {
        if (!finish_called) {
            int ret = LZ_compress_write(encoder, (const uint8_t *)test_data + inpos,
                                        min_int(INT_MAX, (int)(insize - inpos)));
            if (ret < 0) {
                fprintf(stderr, "FAIL: LZ_compress_write error\n");
                LZ_compress_close(encoder);
                return 1;
            }
            inpos += ret;
            if (inpos >= insize) {
                LZ_compress_finish(encoder);
                finish_called = 1;
            }
        }
        int ret = LZ_compress_read(encoder, compressed + comp_pos,
                                   (int)(sizeof(compressed) - comp_pos));
        if (ret < 0) {
            fprintf(stderr, "FAIL: LZ_compress_read error\n");
            LZ_compress_close(encoder);
            return 1;
        }
        comp_pos += ret;
    }
    LZ_compress_close(encoder);

    /* Decompress */
    LZ_Decoder *decoder = LZ_decompress_open();
    if (!decoder || LZ_decompress_errno(decoder) != LZ_ok) {
        fprintf(stderr, "FAIL: LZ_decompress_open failed\n");
        LZ_decompress_close(decoder);
        return 1;
    }

    uint8_t decompressed[4096];
    long decomp_pos = 0;
    long cpos = 0;
    int df_finish_called = 0;

    while (LZ_decompress_finished(decoder) != 1) {
        if (!df_finish_called) {
            int ret = LZ_decompress_write(decoder, compressed + cpos,
                                          min_int(INT_MAX, (int)(comp_pos - cpos)));
            if (ret < 0) {
                fprintf(stderr, "FAIL: LZ_decompress_write error\n");
                LZ_decompress_close(decoder);
                return 1;
            }
            cpos += ret;
            if (cpos >= comp_pos) {
                LZ_decompress_finish(decoder);
                df_finish_called = 1;
            }
        }
        int ret = LZ_decompress_read(decoder, decompressed + decomp_pos,
                                     (int)(sizeof(decompressed) - decomp_pos));
        if (ret < 0) {
            fprintf(stderr, "FAIL: LZ_decompress_read error\n");
            LZ_decompress_close(decoder);
            return 1;
        }
        decomp_pos += ret;
    }
    LZ_decompress_close(decoder);

    /* Verify */
    if (decomp_pos != insize ||
        memcmp(decompressed, test_data, insize) != 0) {
        fprintf(stderr, "FAIL: Decompressed data differs from original\n");
        return 1;
    }

    printf("PASS: lzlib compress/decompress round-trip OK (orig=%ld, comp=%ld, decomp=%ld)\n",
           insize, comp_pos, decomp_pos);
    return 0;
}
