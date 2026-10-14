/*
 * libao 1.2.0 consumer test (Conan L1 / R34).
 *
 * Exercises the installed library the way a downstream package would:
 * initialize the library, resolve the built-in "wav" and "null" drivers by
 * name, write a 1-second 440 Hz 16-bit mono sine wave through the wav driver,
 * push the same samples through the null driver, then re-read the produced
 * file and assert the RIFF/WAVE structure and the exact expected size.
 *
 * No audio hardware is required: the wav driver writes a file and the null
 * driver discards its samples.  Exit codes >= 200 identify the failing
 * assertion so that environment-level exec refusals (rc 1..127, e.g. the
 * hnp sandbox refusing user-path binaries) can be told apart from genuine
 * test failures.
 */
#include <ao/ao.h>

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RATE 44100
#define NSAMPLES RATE /* one second */
#define WAV_HEADER_LEN 68 /* WAVE_FORMAT_EXTENSIBLE: RIFF+fmt(40)+data */

static int checks = 0;

#define CHECK(cond, msg)                                        \
    do {                                                        \
        checks++;                                               \
        if (!(cond)) {                                          \
            fprintf(stderr, "FAIL[%d]: %s\n", checks, msg);     \
            return 200 + checks;                                \
        }                                                       \
    } while (0)

static unsigned int u16le(const unsigned char *p)
{
    return (unsigned int)p[0] | ((unsigned int)p[1] << 8);
}

static unsigned int u32le(const unsigned char *p)
{
    return (unsigned int)p[0] | ((unsigned int)p[1] << 8) |
           ((unsigned int)p[2] << 16) | ((unsigned int)p[3] << 24);
}

int main(int argc, char **argv)
{
    const char *out = argc > 1 ? argv[1] : "libao-consumer.wav";
    unsigned char hdr[WAV_HEADER_LEN];
    unsigned char probe[512];
    long size;
    FILE *f;

    ao_initialize();

    int wav_id = ao_driver_id("wav");
    CHECK(wav_id >= 0, "ao_driver_id(\"wav\") failed");
    int null_id = ao_driver_id("null");
    CHECK(null_id >= 0, "ao_driver_id(\"null\") failed");

    ao_sample_format fmt;
    memset(&fmt, 0, sizeof fmt);
    fmt.bits = 16;
    fmt.channels = 1;
    fmt.rate = RATE;
    fmt.byte_format = AO_FMT_LITTLE;

    ao_device *dev = ao_open_file(wav_id, out, 1, &fmt, NULL);
    CHECK(dev != NULL, "ao_open_file(wav) failed");

    short *buf = (short *)malloc((size_t)NSAMPLES * sizeof(short));
    CHECK(buf != NULL, "malloc failed");
    for (int i = 0; i < NSAMPLES; i++)
        buf[i] = (short)(32767.0 * 0.5 *
                         sin(2.0 * 3.141592653589793 * 440.0 * i / RATE));

    CHECK(ao_play(dev, (char *)buf, (uint_32)(NSAMPLES * sizeof(short))) != 0,
          "ao_play(wav) failed");
    CHECK(ao_close(dev) != 0, "ao_close(wav) failed");

    ao_device *ndev = ao_open_live(null_id, &fmt, NULL);
    CHECK(ndev != NULL, "ao_open_live(null) failed");
    CHECK(ao_play(ndev, (char *)buf, (uint_32)(NSAMPLES * sizeof(short))) != 0,
          "ao_play(null) failed");
    CHECK(ao_close(ndev) != 0, "ao_close(null) failed");

    ao_shutdown();
    free(buf);

    /* ── re-read and validate the produced file ────────────────────────── */
    f = fopen(out, "rb");
    CHECK(f != NULL, "cannot reopen the produced wav file");
    CHECK(fread(hdr, 1, sizeof hdr, f) == sizeof hdr, "short wav header");
    CHECK(memcmp(hdr, "RIFF", 4) == 0, "missing RIFF magic");
    CHECK(memcmp(hdr + 8, "WAVE", 4) == 0, "missing WAVE magic");
    CHECK(memcmp(hdr + 12, "fmt ", 4) == 0, "missing fmt chunk id");
    CHECK(u32le(hdr + 16) == 40, "fmt chunk size != 40");
    CHECK(u16le(hdr + 20) == 0xFFFE, "wFormatTag != WAVE_FORMAT_EXTENSIBLE");
    CHECK(u16le(hdr + 22) == 1, "channel count != 1");
    CHECK(u32le(hdr + 24) == RATE, "sample rate != 44100");
    CHECK(u16le(hdr + 34) == 16, "bits per sample != 16");
    CHECK(memcmp(hdr + 44,
                 "\x01\x00\x00\x00\x00\x00\x10\x00\x80\x00\x00\xaa\x00\x38\x9b\x71",
                 16) == 0,
          "sub-format GUID != PCM");
    CHECK(memcmp(hdr + 60, "data", 4) == 0, "missing data chunk id");
    CHECK(u32le(hdr + 64) == (unsigned int)(2 * NSAMPLES),
          "data chunk size mismatch");
    CHECK(fread(probe, 1, sizeof probe, f) == sizeof probe,
          "cannot read sample data");
    int nonzero = 0;
    for (size_t i = 0; i < sizeof probe; i++)
        nonzero += probe[i] != 0;
    CHECK(nonzero > 0, "sample data is all zero (sine wave not written)");
    fseek(f, 0, SEEK_END);
    size = ftell(f);
    fclose(f);
    CHECK(size == WAV_HEADER_LEN + 2L * NSAMPLES,
          "file size != 68 + 2 * samples");

    printf("LIBAO_CONSUMER_OK checks=%d file=%s size=%ld wav_drv=%d null_drv=%d\n",
           checks, out, size, wav_id, null_id);
    return 0;
}
