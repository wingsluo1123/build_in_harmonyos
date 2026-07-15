#include <stdio.h>
#include <stdlib.h>
#include <mpg123.h>

int main(void) {
    int err;
    err = mpg123_init();
    if (err != MPG123_OK) {
        fprintf(stderr, "mpg123_init failed: %s\n", mpg123_plain_strerror(err));
        return 1;
    }
    mpg123_handle *mh = mpg123_new(NULL, &err);
    if (mh == NULL) {
        fprintf(stderr, "mpg123_new failed: %s\n", mpg123_plain_strerror(err));
        mpg123_cleanup();
        return 1;
    }
    printf("mpg123 version: %s\n", mpg123_decode_version(mh));
    mpg123_delete(mh);
    mpg123_cleanup();
    printf("test mpg123 1.33.6: OK\n");
    return 0;
}
