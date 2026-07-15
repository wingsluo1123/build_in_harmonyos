#include <stdio.h>
#include <string.h>
#include "rhash.h"

int main(void) {
    rhash_library_init();

    /* Compute MD5 of "hello" */
    unsigned char result[32];
    int ret = rhash_msg(RHASH_MD5, "hello", 5, result);
    if (ret != 0) {
        printf("FAIL: rhash_msg returned %d\n", ret);
        return 1;
    }

    /* MD5("hello") = 5d41402abc4b2a76b9719d911017c592 */
    char hex[33];
    for (int i = 0; i < 16; i++) {
        sprintf(hex + i * 2, "%02x", result[i]);
    }
    hex[32] = '\0';

    if (strcmp(hex, "5d41402abc4b2a76b9719d911017c592") == 0) {
        printf("PASS: MD5(\"hello\") = %s\n", hex);
        return 0;
    } else {
        printf("FAIL: MD5 mismatch, got %s\n", hex);
        return 1;
    }
}
