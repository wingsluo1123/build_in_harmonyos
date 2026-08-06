#include <libmp3splt/mp3splt.h>
#include <stdio.h>

int main() {
    mp3splt_state *state = NULL;
    int err = mp3splt_init(&state);
    if (err != 0) {
        fprintf(stderr, "mp3splt_init failed with error %d\n", err);
        return 1;
    }
    if (state) {
        mp3splt_free(state);
    }
    printf("libmp3splt test OK\n");
    return 0;
}
