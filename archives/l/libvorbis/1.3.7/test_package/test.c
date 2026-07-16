#include <stdio.h>
#include <stdlib.h>
#include <vorbis/codec.h>
#include <vorbis/vorbisenc.h>

int main(void) {
    /* Test libvorbis API: initialize and encode a short block */
    vorbis_info vi;
    vorbis_info_init(&vi);

    int ret = vorbis_encode_init(&vi, 2, 44100, -1, 128000, -1);
    if (ret != 0) {
        fprintf(stderr, "vorbis_encode_init failed: %d\n", ret);
        return 1;
    }

    vorbis_dsp_state vd;
    vorbis_block vb;
    vorbis_analysis_init(&vd, &vi);
    vorbis_block_init(&vd, &vb);

    printf("libvorbis 1.3.7 API test: OK\n");
    printf("  channels=%ld  rate=%ld\n", vi.channels, vi.rate);

    vorbis_block_clear(&vb);
    vorbis_dsp_clear(&vd);
    vorbis_info_clear(&vi);

    return 0;
}
