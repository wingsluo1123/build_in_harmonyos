#include <stdio.h>
#include <gst/gst.h>
#include <gst/audio/audio-format.h>

int main(void) {
    /* Initialize GStreamer (required before using any GStreamer API) */
    gst_init(NULL, NULL);

    /* Call a gst-plugins-base API: gst_audio_format_to_string() */
    const gchar *fmt_str = gst_audio_format_to_string(GST_AUDIO_FORMAT_S16);
    if (fmt_str == NULL) {
        fprintf(stderr, "FAIL: gst_audio_format_to_string returned NULL\n");
        return 1;
    }

    printf("gst_audio_format_to_string(S16) = %s\n", fmt_str);

    /* Verify we can get format info (another gst-plugins-base API) */
    const GstAudioFormatInfo *info = gst_audio_format_get_info(GST_AUDIO_FORMAT_S16);
    if (info == NULL) {
        fprintf(stderr, "FAIL: gst_audio_format_get_info returned NULL\n");
        return 1;
    }

    printf("S16: depth=%u, width=%u, endianness=%u\n",
           info->depth, info->width, info->endianness);

    /* Also test gst_audio_format_from_string (round-trip) */
    GstAudioFormat fmt = gst_audio_format_from_string(fmt_str);
    if (fmt != GST_AUDIO_FORMAT_S16) {
        fprintf(stderr, "FAIL: round-trip format mismatch\n");
        return 1;
    }

    printf("test gst-plugins-base 1.28.3: OK\n");
    return 0;
}
