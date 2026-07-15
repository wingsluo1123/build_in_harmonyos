#include <stdio.h>
#include <string.h>
#include "bcrypt.h"

int main(void) {
    char salt[BCRYPT_HASHSIZE];
    char hash[BCRYPT_HASHSIZE];
    int ret;

    /* Generate a salt with work factor 6 (fast for testing) */
    ret = bcrypt_gensalt(6, salt);
    if (ret != 0) {
        fprintf(stderr, "bcrypt_gensalt failed\n");
        return 1;
    }

    /* Hash a password */
    ret = bcrypt_hashpw("testpassword", salt, hash);
    if (ret != 0) {
        fprintf(stderr, "bcrypt_hashpw failed\n");
        return 1;
    }

    /* Verify the password matches */
    ret = bcrypt_checkpw("testpassword", hash);
    if (ret != 0) {
        fprintf(stderr, "bcrypt_checkpw: password verification failed (ret=%d)\n", ret);
        return 1;
    }

    /* Verify wrong password does not match */
    ret = bcrypt_checkpw("wrongpassword", hash);
    if (ret == 0) {
        fprintf(stderr, "bcrypt_checkpw: wrong password incorrectly matched\n");
        return 1;
    }

    printf("libbcrypt test: ALL PASSED\n");
    return 0;
}
