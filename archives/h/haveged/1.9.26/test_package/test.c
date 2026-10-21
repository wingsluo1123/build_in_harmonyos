#include <haveged/havege.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    H_PARAMS params;
    memset(&params, 0, sizeof(params));
    if (havege_version(NULL) == NULL) {
        fprintf(stderr, "havege_version returned NULL\n");
        return 1;
    }
    H_PTR state = havege_create(&params);
    if (state == NULL || state->error != H_NOERR) {
        fprintf(stderr, "havege_create failed\n");
        if (state != NULL) havege_destroy(state);
        return 2;
    }
    if (havege_run(state) != 0) {
        fprintf(stderr, "havege_run failed: %d\n", state->error);
        havege_destroy(state);
        return 3;
    }
    if (state->i_readSz < 32 * sizeof(H_UINT) ||
        havege_rng(state, state->io_buf, 32) != 32) {
        fprintf(stderr, "havege_rng failed: %d\n", state->error);
        havege_destroy(state);
        return 4;
    }
    H_UINT combined = 0;
    for (unsigned int i = 0; i < 32; ++i) combined |= state->io_buf[i];
    havege_destroy(state);
    if (combined == 0) {
        fprintf(stderr, "havege_rng returned 32 zero words\n");
        return 5;
    }
    puts("libhavege consumer: 32 words generated");
    return 0;
}
