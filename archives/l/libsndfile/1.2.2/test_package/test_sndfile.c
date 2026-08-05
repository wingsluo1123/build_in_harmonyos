/*
 * test_sndfile — Consumer test for libsndfile conan package.
 * Verifies sf_open / sf_read_double / sf_write_double API.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sndfile.h>

int main(void)
{
    const char *ver = sf_version_string();
    if (!ver) {
        fprintf(stderr, "sf_version_string returned NULL\n");
        return 1;
    }
    printf("libsndfile version: %s\n", ver);

    const char *tmpdir = getenv("TMPDIR");
    if (!tmpdir) tmpdir = "/tmp";
    char tmppath[512];
    snprintf(tmppath, sizeof(tmppath), "%s/conan_sndfile_test.wav", tmpdir);

    SF_INFO sfinfo;
    memset(&sfinfo, 0, sizeof(sfinfo));
    sfinfo.samplerate = 44100;
    sfinfo.channels   = 1;
    sfinfo.format     = SF_FORMAT_WAV | SF_FORMAT_PCM_16;

    SNDFILE *outfile = sf_open(tmppath, SFM_WRITE, &sfinfo);
    if (!outfile) {
        fprintf(stderr, "sf_open(SFM_WRITE) failed: %s\n", sf_strerror(NULL));
        return 2;
    }

    double buffer[256];
    for (int i = 0; i < 256; i++) buffer[i] = 0.0;
    sf_count_t written = sf_write_double(outfile, buffer, 256);
    sf_close(outfile);
    if (written != 256) {
        fprintf(stderr, "sf_write_double wrote %%lld instead of 256\n", (long long)written);
        remove(tmppath);
        return 3;
    }

    SF_INFO readinfo;
    memset(&readinfo, 0, sizeof(readinfo));
    SNDFILE *infile = sf_open(tmppath, SFM_READ, &readinfo);
    if (!infile) {
        fprintf(stderr, "sf_open(SFM_READ) failed: %s\n", sf_strerror(NULL));
        remove(tmppath);
        return 4;
    }

    double readbuf[256];
    sf_count_t count = sf_read_double(infile, readbuf, 256);
    sf_close(infile);
    remove(tmppath);
    if (count != 256) {
        fprintf(stderr, "sf_read_double read %%lld instead of 256\n", (long long)count);
        return 5;
    }

    printf("libsndfile test passed: wrote and read 256 samples at %d Hz\n", readinfo.samplerate);
    return 0;
}
