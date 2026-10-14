#include <stdio.h>
#include <sox_ng.h>

int main(void)
{
    const sox_version_info_t *version;

    if (sox_init() != SOX_SUCCESS) {
        fputs("sox_init failed\n", stderr);
        return 1;
    }

    if (sox_find_format("wav", sox_false) == NULL) {
        fputs("WAV format handler is missing\n", stderr);
        sox_quit();
        return 2;
    }
    if (sox_find_effect("vol") == NULL) {
        fputs("volume effect handler is missing\n", stderr);
        sox_quit();
        return 3;
    }

    version = sox_version_info();
    if (version == NULL || version->version == NULL) {
        fputs("version information is missing\n", stderr);
        sox_quit();
        return 4;
    }

    printf("libSoX NG %s: WAV and vol handlers available\n", version->version);
    return sox_quit() == SOX_SUCCESS ? 0 : 5;
}
