#include <stdio.h>
#include <gsm.h>

int main(void) {
    /* Create a gsm encoder state */
    gsm encoder = gsm_create();
    if (!encoder) {
        fprintf(stderr, "gsm_create() failed\n");
        return 1;
    }

    /* Encode 160 samples (20ms of audio at 8kHz) of silence */
    gsm_signal input[160] = {0};
    gsm_frame frame;
    gsm_encode(encoder, input, frame);

    /* Decode the frame back */
    gsm decoder = gsm_create();
    if (!decoder) {
        fprintf(stderr, "gsm_create() for decoder failed\n");
        gsm_destroy(encoder);
        return 1;
    }

    gsm_signal output[160];
    int ret = gsm_decode(decoder, frame, output);
    if (ret != 0) {
        fprintf(stderr, "gsm_decode() returned %d\n", ret);
        gsm_destroy(encoder);
        gsm_destroy(decoder);
        return 1;
    }

    /* Verify: decoded output should be near-silence (all zeros or very small) */
    int max_val = 0;
    for (int i = 0; i < 160; i++) {
        int v = output[i] < 0 ? -output[i] : output[i];
        if (v > max_val) max_val = v;
    }

    gsm_destroy(encoder);
    gsm_destroy(decoder);

    /* Silence input should produce near-silence output */
    if (max_val > 100) {
        fprintf(stderr, "Decoded signal too large: max=%d\n", max_val);
        return 1;
    }

    printf("gsm encode/decode roundtrip OK, max decoded amplitude: %d\n", max_val);
    return 0;
}
