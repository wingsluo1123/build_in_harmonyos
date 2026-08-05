/*
 * Test that genuinely calls libmad API: init decoder, run, finish, check version.
 */
#include <mad.h>
#include <stdio.h>
#include <string.h>

static enum mad_flow input_cb(void *data, struct mad_stream *stream)
{
    return MAD_FLOW_STOP;
}

static enum mad_flow output_cb(void *data,
                               struct mad_header const *header,
                               struct mad_pcm *pcm)
{
    return MAD_FLOW_STOP;
}

static enum mad_flow error_cb(void *data,
                              struct mad_stream *stream,
                              struct mad_frame *frame)
{
    return MAD_FLOW_CONTINUE;
}

int main(void)
{
    struct mad_decoder decoder;

    mad_decoder_init(&decoder, NULL,
                     input_cb, 0, 0,
                     output_cb, error_cb, 0);

    int result = mad_decoder_run(&decoder, MAD_DECODER_MODE_SYNC);

    mad_decoder_finish(&decoder);

    if (result != 0) {
        printf("mad_decoder_run returned %d (expected 0)\n", result);
        return 1;
    }

    if (strstr(mad_version, "0.16") == NULL) {
        printf("ERROR: unexpected version string: %s\n", mad_version);
        return 1;
    }

    printf("libmad version: %s\n", mad_version);
    printf("libmad decoder init/run/finish: OK\n");
    return 0;
}
