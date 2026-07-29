#include <sndfile.h>

#include <stdio.h>

int main(void) {
    SF_INFO info = {0};
    const char *version = sf_version_string();

    if (version == NULL || version[0] == '\0') {
        fprintf(stderr, "libsndfile returned an empty version string\n");
        return 1;
    }

    info.samplerate = 44100;
    info.channels = 2;
    info.format = SF_FORMAT_WAV | SF_FORMAT_PCM_16;
    if (!sf_format_check(&info)) {
        fprintf(stderr, "libsndfile rejected a standard WAV/PCM format\n");
        return 1;
    }

    printf("libsndfile version: %s\n", version);
    return 0;
}
