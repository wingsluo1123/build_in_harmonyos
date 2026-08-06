// test.c — Minimal test that links against mp3splt-gtk's dependency (libmp3splt)
// Verifies the package's transitive dependencies are available
#include <libmp3splt/mp3splt.h>

int main() {
    // Just verify the header is accessible
    mp3splt_state *state = NULL;
    // mp3splt_init is the basic API call
    int err = mp3splt_init(&state);
    if (state) {
        mp3splt_free(state);
    }
    return 0;
}
