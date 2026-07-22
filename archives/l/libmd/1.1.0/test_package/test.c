/*
 * R34 test for libmd 1.1.0 — real API exercise.
 *
 * libmd provides MD5/SHA hash functions. This test calls MD5Data() on a
 * known input and compares against the canonical MD5 of "hello",
 * exercising symbol resolution + ABI at runtime. A broken/stripped
 * libmd will fail here rather than silently print "OK".
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <md5.h>

int main(void) {
    const char *data = "hello";
    char *hash = MD5Data((const unsigned char *)data, strlen(data), NULL);
    if (hash == NULL) {
        fprintf(stderr, "FAIL: MD5Data returned NULL\n");
        return 1;
    }
    /* Canonical MD5 of "hello" */
    int ok = (strcmp(hash, "5d41402abc4b2a76b9719d911017c592") == 0);
    if (!ok) {
        fprintf(stderr, "FAIL: MD5 mismatch got %s\n", hash);
        free(hash);
        return 1;
    }
    free(hash);
    printf("libmd 1.1.0: OK\n");
    return 0;
}
