#include <stdio.h>
#include <sndfile.h>

int main(void) {
    SF_INFO sfinfo;
    SNDFILE *file;
    sfinfo.format = 0;

    printf("libsndfile version: %s\n", sf_version_string());

    /* Create a simple WAV file */
    sfinfo.samplerate = 44100;
    sfinfo.channels = 1;
    sfinfo.format = SF_FORMAT_WAV | SF_FORMAT_PCM_16;

    file = sf_open("/tmp/test_sndfile_out.wav", SFM_WRITE, &sfinfo);
    if (!file) {
        printf("Failed to open for write: %s\n", sf_strerror(NULL));
        return 1;
    }

    double buffer[256];
    for (int i = 0; i < 256; i++)
        buffer[i] = 0.5;

    sf_count_t written = sf_write_double(file, buffer, 256);
    sf_close(file);

    /* Read it back */
    sfinfo.format = 0;
    file = sf_open("/tmp/test_sndfile_out.wav", SFM_READ, &sfinfo);
    if (!file) {
        printf("Failed to open for read: %s\n", sf_strerror(NULL));
        return 1;
    }

    double read_buf[256];
    sf_count_t read_count = sf_read_double(file, read_buf, 256);
    sf_close(file);

    printf("libsndfile test passed: wrote and read %lld samples at %d Hz\n",
           (long long)read_count, sfinfo.samplerate);

    return 0;
}
