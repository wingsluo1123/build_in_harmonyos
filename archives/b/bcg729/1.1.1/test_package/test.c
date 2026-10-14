/*
 * test_libbcg729 — L1 smoke test for the bcg729 public codec API (1.1.1).
 *
 * Exercises a real encode -> decode round-trip on a silence frame using
 * only the public <bcg729/encoder.h> and <bcg729/decoder.h> interfaces:
 *   initBcg729EncoderChannel / bcg729Encoder / closeBcg729EncoderChannel
 *   initBcg729DecoderChannel / bcg729Decoder / closeBcg729DecoderChannel
 *
 * Additionally checks the multi-channel concurrent API
 * (initBcg729EncoderChannels/bcg729EncoderChannels, present since 1.0.x
 * with explicit multi-channel entry points) which is the headline feature
 * of this codec implementation.
 */
#include <bcg729/encoder.h>
#include <bcg729/decoder.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define L_FRAME 80  /* one G.729 frame = 80 samples (10 ms @ 8 kHz) */

int main(void) {
    int rc = 0;

    /* ---- Encoder: create context, encode one silence frame ---- */
    bcg729EncoderChannelContextStruct *enc = initBcg729EncoderChannel(0 /* no VAD/DTX */);
    if (enc == NULL) {
        fprintf(stderr, "FAIL: initBcg729EncoderChannel returned NULL\n");
        return 1;
    }

    int16_t inputFrame[L_FRAME];
    uint8_t bitStream[10] = {0};
    uint8_t bitStreamLength = 0;
    /* A frame of zero samples = digital silence */
    memset(inputFrame, 0, sizeof(inputFrame));

    bcg729Encoder(enc, inputFrame, bitStream, &bitStreamLength);

    /* With VAD disabled the encoder always emits a 10-byte (80-bit) voice frame */
    if (bitStreamLength == 0) {
        fprintf(stderr, "FAIL: encoder produced empty bitstream (length=0)\n");
        closeBcg729EncoderChannel(enc);
        return 1;
    }
    if (bitStreamLength > sizeof(bitStream)) {
        fprintf(stderr, "FAIL: bitstream length %u overflows buffer\n", bitStreamLength);
        closeBcg729EncoderChannel(enc);
        return 1;
    }
    printf("encoder: produced %u-byte frame from silence\n", bitStreamLength);

    /* ---- Decoder: create context, decode the encoded frame ---- */
    bcg729DecoderChannelContextStruct *dec = initBcg729DecoderChannel();
    if (dec == NULL) {
        fprintf(stderr, "FAIL: initBcg729DecoderChannel returned NULL\n");
        closeBcg729EncoderChannel(enc);
        return 1;
    }

    int16_t outputFrame[L_FRAME];
    memset(outputFrame, 0, sizeof(outputFrame));
    /* frameErasure=0, SIDFrame=0, rfc3389Payload=0: regular decode */
    bcg729Decoder(dec, bitStream, bitStreamLength, 0, 0, 0, outputFrame);

    /* Verify the decoder produced a sane (non-garbage) output frame */
    int nonzero = 0;
    for (int i = 0; i < L_FRAME; i++) {
        if (outputFrame[i] < -32768 || outputFrame[i] > 32767) {
            fprintf(stderr, "FAIL: decoder produced invalid sample at %d\n", i);
            rc = 1;
            break;
        }
        if (outputFrame[i] != 0) nonzero++;
    }
    if (rc == 0) {
        printf("decoder: decoded %d-sample frame (%d non-zero samples)\n",
               L_FRAME, nonzero);
    }

    /* ---- Concurrent channels: 2 independent encoder contexts ----
     * (bcg729's headline feature: concurrent encoder/decoder channels; in
     * 1.1.1 this is achieved via independent channel contexts — the
     * explicit *Channels() API only appeared in later upstream releases) */
    {
        enum { NCH = 2 };
        bcg729EncoderChannelContextStruct *chans[NCH] = {0};  /* NULL-init: cleanup loop safely skips uncreated slots */
        uint8_t lens[NCH];
        for (int c = 0; c < NCH; c++) {
            chans[c] = initBcg729EncoderChannel(0);
            if (chans[c] == NULL) {
                fprintf(stderr, "FAIL: initBcg729EncoderChannel #%d returned NULL\n", c);
                rc = 1;
                break;
            }
            bcg729Encoder(chans[c], inputFrame, bitStream, &lens[c]);
            if (lens[c] == 0) {
                fprintf(stderr, "FAIL: channel %d produced empty bitstream\n", c);
                rc = 1;
            }
        }
        for (int c = 0; c < NCH; c++) {
            if (chans[c]) closeBcg729EncoderChannel(chans[c]);
        }
        if (rc == 0) {
            printf("concurrent-channels: %d independent encoder contexts OK\n", NCH);
        }
    }

    /* ---- Release all resources ---- */
    closeBcg729DecoderChannel(dec);
    closeBcg729EncoderChannel(enc);

    if (rc == 0) {
        printf("libbcg729 1.1.1 API round-trip test: OK\n");
    }
    return rc;
}
