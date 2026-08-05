#include <stdio.h>
#include <mad.h>
static enum mad_flow input_cb(void *msg, struct mad_stream *stream) {
    (void)msg; (void)stream; return MAD_FLOW_STOP;
}
int main(void) {
    if (mad_version_string == NULL || mad_version_string[0] == '\0') { printf("FAIL\n"); return 1; }
    printf("mad version: %s\n", mad_version_string);
    struct mad_decoder decoder;
    mad_decoder_init(&decoder, NULL, input_cb, NULL, NULL, NULL, NULL, NULL);
    int ret = mad_decoder_run(&decoder, MAD_DECODER_MODE_SYNC);
    if (ret != MAD_FLOW_STOP) { printf("FAIL: mad_decoder_run returned %d\n", ret); mad_decoder_finish(&decoder); return 1; }
    mad_decoder_finish(&decoder);
    printf("test libmad 0.16.4: OK\n");
    return 0;
}
