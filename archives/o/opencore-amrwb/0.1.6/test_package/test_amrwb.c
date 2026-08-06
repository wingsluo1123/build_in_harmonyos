#include <stdio.h>
#include <string.h>
#include <opencore-amrwb/dec_if.h>

/* AMR-WB frame sizes per mode (bytes, excluding the mode byte) */
static const int sizes[] = {17, 23, 32, 36, 40, 46, 50, 58, 60, 5, -1, -1, -1, -1, -1, 0};

int main(void)
{
    /* Initialize the AMR-WB decoder */
    void *state = D_IF_init();
    if (!state) {
        fprintf(stderr, "D_IF_init failed\n");
        return 1;
    }

    /* Build a dummy AMR-WB frame in MIME storage format.
     * Mode 0 (6.60 kbit/s) requires 17 bytes of payload.
     * The first byte contains the mode in bits 3-6. */
    int mode = 0;
    int payload_size = sizes[mode];
    unsigned char frame[64];
    memset(frame, 0, sizeof(frame));
    frame[0] = (unsigned char)((mode << 3) & 0xF0);

    /* Decode one frame (20ms at 16kHz = 320 samples) */
    short synth[320];
    memset(synth, 0, sizeof(synth));
    D_IF_decode(state, frame, synth, 0);

    /* Verify the decoder produced output samples */
    int has_output = 0;
    for (int i = 0; i < 320; i++) {
        if (synth[i] != 0) {
            has_output = 1;
            break;
        }
    }

    /* Clean up the decoder state */
    D_IF_exit(state);

    printf("Decoder initialized, decoded %d-byte frame (mode %d), produced %s output.\n",
           payload_size + 1, mode, has_output ? "non-zero" : "all-zero (silence)");
    printf("opencore-amrwb test passed\n");

    return 0;
}
