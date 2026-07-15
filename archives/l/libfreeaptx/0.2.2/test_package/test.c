#include <stdio.h>
#include <string.h>
#include <freeaptx.h>

int main(void) {
    /* Test 1: Check version constants */
    if (aptx_major != 0 || aptx_minor != 2 || aptx_patch != 2) {
        printf("FAIL: version mismatch: %d.%d.%d\n", aptx_major, aptx_minor, aptx_patch);
        return 1;
    }

    /* Test 2: Initialize aptX encoder context (standard aptX, hd=0) */
    struct aptx_context *enc_ctx = aptx_init(0);
    if (!enc_ctx) {
        printf("FAIL: aptx_init(0) returned NULL\n");
        return 1;
    }

    /* Test 3: Encode 4 raw 24-bit stereo samples (24 bytes input) */
    unsigned char input[24] = {0};
    unsigned char output[16] = {0};
    size_t written = 0;
    size_t processed = aptx_encode(enc_ctx, input, sizeof(input), output, sizeof(output), &written);
    if (processed != 24) {
        printf("FAIL: aptx_encode processed %zu, expected 24\n", processed);
        aptx_finish(enc_ctx);
        return 1;
    }
    if (written == 0) {
        printf("FAIL: aptx_encode wrote 0 bytes\n");
        aptx_finish(enc_ctx);
        return 1;
    }

    /* Test 4: Initialize aptX decoder context */
    struct aptx_context *dec_ctx = aptx_init(0);
    if (!dec_ctx) {
        printf("FAIL: aptx_init(0) decoder returned NULL\n");
        aptx_finish(enc_ctx);
        return 1;
    }

    /* Test 5: Decode the encoded aptX data */
    unsigned char decoded[24] = {0};
    size_t dec_written = 0;
    size_t dec_processed = aptx_decode(dec_ctx, output, written, decoded, sizeof(decoded), &dec_written);
    if (dec_processed != written) {
        printf("FAIL: aptx_decode processed %zu, expected %zu\n", dec_processed, written);
        aptx_finish(enc_ctx);
        aptx_finish(dec_ctx);
        return 1;
    }

    /* Test 6: Cleanup */
    aptx_finish(enc_ctx);
    aptx_finish(dec_ctx);

    printf("test libfreeaptx 0.2.2: OK (encode %zu bytes, decode %zu bytes)\n", written, dec_written);
    return 0;
}
