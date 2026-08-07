#include <pulse/pulseaudio.h>
#include <stdio.h>

int main() {
    /* Test that we can link against libpulse and call its API */
    pa_mainloop *ml = pa_mainloop_new();
    if (!ml) {
        fprintf(stderr, "Failed to create mainloop\n");
        return 1;
    }
    pa_mainloop_api *api = pa_mainloop_get_api(ml);
    if (!api) {
        fprintf(stderr, "Failed to get mainloop API\n");
        pa_mainloop_free(ml);
        return 1;
    }
    printf("libpulse version: %s\n", pa_get_library_version());
    pa_mainloop_free(ml);
    return 0;
}
