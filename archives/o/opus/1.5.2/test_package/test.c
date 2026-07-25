/* opus test_package：真实编解码往返，非仅版本查询（R34 / R40 多媒体类要求） */
#include <opus/opus.h>

#include <stdio.h>

#define SR      48000
#define CH      2
#define FRAME   960          /* 20ms @ 48kHz */

int main(void) {
    int err = 0;

    OpusEncoder *enc = opus_encoder_create(SR, CH, OPUS_APPLICATION_AUDIO, &err);
    if (enc == NULL || err != OPUS_OK) {
        fprintf(stderr, "opus_encoder_create failed: %d (%s)\n", err, opus_strerror(err));
        return 1;
    }

    /* 造一段可辨识的 PCM（非全零，避免编码器走静音短路） */
    static opus_int16 pcm[FRAME * CH];
    for (int i = 0; i < FRAME * CH; i++) {
        pcm[i] = (opus_int16)(((i * 37) % 2048) - 1024);
    }

    unsigned char packet[4000];
    int nbytes = opus_encode(enc, pcm, FRAME, packet, (opus_int32)sizeof(packet));
    opus_encoder_destroy(enc);
    if (nbytes <= 2) {
        fprintf(stderr, "opus_encode failed or produced empty packet: %d\n", nbytes);
        return 1;
    }

    OpusDecoder *dec = opus_decoder_create(SR, CH, &err);
    if (dec == NULL || err != OPUS_OK) {
        fprintf(stderr, "opus_decoder_create failed: %d (%s)\n", err, opus_strerror(err));
        return 1;
    }

    static opus_int16 back[FRAME * CH];
    int nsamples = opus_decode(dec, packet, nbytes, back, FRAME, 0);
    opus_decoder_destroy(dec);
    if (nsamples != FRAME) {
        fprintf(stderr, "opus_decode returned %d, expected %d\n", nsamples, FRAME);
        return 1;
    }

    printf("opus: version=%s  encode=%d bytes  decode=%d samples/ch  OK\n",
           opus_get_version_string(), nbytes, nsamples);
    return 0;
}
