#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <opencore-amrnb/interf_enc.h>
#include <opencore-amrnb/interf_dec.h>
#include <opencore-amrwb/dec_if.h>

int main(void) {
    /* Test AMR-NB encoder/decoder round-trip */
    void *enc = Encoder_Interface_init(0);
    if (!enc) {
        fprintf(stderr, "AMR-NB encoder init failed\n");
        return 1;
    }

    short speech[160] = {0};
    unsigned char amr[32] = {0};
    int n = Encoder_Interface_Encode(enc, MR122, speech, amr, 0);
    if (n <= 0) {
        fprintf(stderr, "AMR-NB encode failed\n");
        Encoder_Interface_exit(enc);
        return 1;
    }
    Encoder_Interface_exit(enc);

    void *dec = Decoder_Interface_init();
    if (!dec) {
        fprintf(stderr, "AMR-NB decoder init failed\n");
        return 1;
    }
    short out_pcm[160] = {0};
    Decoder_Interface_Decode(dec, amr, out_pcm, 0);
    Decoder_Interface_exit(dec);

    /* Test AMR-WB decoder init/exit */
    void *wb_dec = D_IF_init();
    if (!wb_dec) {
        fprintf(stderr, "AMR-WB decoder init failed\n");
        return 1;
    }
    D_IF_exit(wb_dec);

    printf("opencore-amr 0.1.6 test: AMR-NB encode(%d bytes) + decode + AMR-WB init OK\n", n);
    return 0;
}
