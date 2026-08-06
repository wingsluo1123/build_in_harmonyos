#include <stdio.h>
#include <stdlib.h>

/* mpg123 library header */
#include <mpg123.h>

int main(void) {
    /* Initialize the mpg123 library - this calls the actual library API */
    int ret = mpg123_init();
    if (ret != MPG123_OK) {
        fprintf(stderr, "mpg123_init() failed: %s\n", mpg123_plain_strerror(ret));
        return EXIT_FAILURE;
    }

    /* Create a new mpg123 handle to verify the API works */
    int err;
    mpg123_handle *mh = mpg123_new(NULL, &err);
    if (mh == NULL) {
        fprintf(stderr, "mpg123_new() failed: %s\n", mpg123_plain_strerror(err));
        mpg123_exit();
        return EXIT_FAILURE;
    }

    /* Get version info to verify linking worked */
    unsigned int major, minor, patch;
    const char *ver = mpg123_distversion(&major, &minor, &patch);
    printf("mpg123 version: %s (%u.%u.%u)\n", ver, major, minor, patch);

    /* Clean up */
    mpg123_delete(mh);
    mpg123_exit();

    printf("mpg123 library test passed!\n");
    return EXIT_SUCCESS;
}
