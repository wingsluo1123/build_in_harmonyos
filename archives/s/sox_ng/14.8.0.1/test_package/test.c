/**
 * sox_ng consumer test: simulate an upper-layer component converting
 * wav -> wav using only the sox_ng public API (sox_ng.h).
 *
 * API notes (sox_ng 14.8.0.1, differs from classic sox):
 * - sox_open_read/sox_open_write return sox_format_t * (session handle)
 * - sox_read/sox_write/sox_close take sox_format_t *
 * - sox_sample_t is sox_int32_t (not double)
 * - construct sox_signalinfo_t explicitly (no sox_signalinfo_empty)
 *
 * Success criteria: compile + link + run, and a real wav->wav conversion
 * round-trips the expected number of samples.
 */
#include <sox_ng.h>

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SOXNG_RATE 44100.0
#define SOXNG_CHANNELS 1
#define SOXNG_SAMPLES 800

static int write_test_wav(const char *path)
{
    /* RIFF/WAVE PCM16 mono 440Hz sine, SOXNG_SAMPLES samples */
    FILE *f = fopen(path, "wb");
    if (!f)
        return -1;
    const uint32_t data_bytes = SOXNG_SAMPLES * SOXNG_CHANNELS * 2;
    uint8_t hdr[44] = {0};
    const char riff[] = "RIFF";
    const char wave[] = "WAVE";
    const char fmt[] = "fmt ";
    const char data[] = "data";
    uint32_t riff_size = 36 + data_bytes;
    uint16_t audio_format = 1, bits = 16;
    uint32_t rate = 44100, block_align = 2, byte_rate = 88200;
    uint16_t channels = 1;

    memcpy(hdr, riff, 4);
    hdr[4] = riff_size & 0xFF; hdr[5] = (riff_size >> 8) & 0xFF;
    hdr[6] = (riff_size >> 16) & 0xFF; hdr[7] = (riff_size >> 24) & 0xFF;
    memcpy(hdr + 8, wave, 4);
    memcpy(hdr + 12, fmt, 4);
    hdr[16] = 16; /* fmt chunk size */
    memcpy(hdr + 20, &audio_format, 2);
    memcpy(hdr + 22, &channels, 2);
    memcpy(hdr + 24, &rate, 4);
    memcpy(hdr + 28, &byte_rate, 4);
    memcpy(hdr + 32, &block_align, 2);
    memcpy(hdr + 34, &bits, 2);
    memcpy(hdr + 36, data, 4);
    hdr[40] = data_bytes & 0xFF; hdr[41] = (data_bytes >> 8) & 0xFF;
    hdr[42] = (data_bytes >> 16) & 0xFF; hdr[43] = (data_bytes >> 24) & 0xFF;
    fwrite(hdr, 1, 44, f);
    for (int i = 0; i < SOXNG_SAMPLES; i++) {
        int16_t s = (int16_t)(30000.0 * sin(2.0 * M_PI * 440.0 * i / rate));
        fwrite(&s, 1, 2, f);
    }
    fclose(f);
    return 0;
}

static void cleanup(sox_format_t *fin, sox_format_t *fout)
{
    if (fin)
        sox_close(fin);
    if (fout)
        sox_close(fout);
    sox_format_quit();
    sox_quit();
}

int main(int argc, char **argv)
{
    (void)argc;
    (void)argv;
    /* Relative paths: cwd is the test build folder; /tmp is read-only on OHOS (E002) */
    const char *in = "./sox_ng_consumer_in.wav";
    const char *out = "./sox_ng_consumer_out.wav";

    if (write_test_wav(in) != 0) {
        fprintf(stderr, "failed to create input wav %s\n", in);
        return 1;
    }

    if (sox_init() != SOX_SUCCESS) {
        fprintf(stderr, "sox_init failed\n");
        return 1;
    }
    if (sox_format_init() != SOX_SUCCESS) {
        fprintf(stderr, "sox_format_init failed\n");
        sox_quit();
        return 1;
    }

    /* Decoding session: NULL signal/encoding -> auto-detect from file */
    sox_format_t *fin = sox_open_read(in, NULL, NULL, NULL);
    if (!fin) {
        fprintf(stderr, "sox_open_read(%s) failed\n", in);
        cleanup(NULL, NULL);
        return 1;
    }

    sox_signalinfo_t sig;
    memset(&sig, 0, sizeof(sig));
    sig.rate = SOXNG_RATE;
    sig.channels = SOXNG_CHANNELS;
    sig.precision = 0; /* format default */
    sig.length = 0;
    sig.mult = NULL;

    remove(out); /* fresh output; overwrite_permitted callback not needed */
    sox_format_t *fout = sox_open_write(out, &sig, NULL, NULL, NULL, NULL);
    if (!fout) {
        fprintf(stderr, "sox_open_write(%s) failed\n", out);
        cleanup(fin, NULL);
        return 1;
    }

    sox_sample_t buf[4096];
    size_t total = 0, r;
    while ((r = sox_read(fin, buf, sizeof(buf) / sizeof(buf[0]))) > 0) {
        size_t w = sox_write(fout, buf, r);
        if (w != r) {
            fprintf(stderr, "sox_write short: wrote %zu of %zu\n", w, r);
            cleanup(fin, fout);
            return 1;
        }
        total += r;
    }

    cleanup(fin, fout);

    if (total != (size_t)SOXNG_SAMPLES) {
        fprintf(stderr, "unexpected sample count: %zu (expected %d)\n",
                total, SOXNG_SAMPLES);
        return 1;
    }
    printf("sox_ng consumer test OK: converted %zu samples wav->wav -> %s\n",
           total, out);
    return 0;
}
