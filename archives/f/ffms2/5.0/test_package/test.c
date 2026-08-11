#include <stdio.h>
#include <string.h>

/* ffms2 public API header */
#include <ffms.h>

int main(void) {
    /* FFMS_Init: initialise the library (both args 0 for current ABI) */
    FFMS_Init(0, 0);

    /* FFMS_GetVersion: verify the library is loaded and returns 5.0.x */
    int ver = FFMS_GetVersion();
    int major = (ver >> 24) & 0xFF;
    int minor = (ver >> 16) & 0xFF;

    if (major != 5) {
        fprintf(stderr, "FAIL: expected ffms2 major version 5, got %d\n", major);
        return 1;
    }

    printf("ffms2 version: %d.%d.%d (raw=0x%08X)\n",
           major, minor, (ver >> 8) & 0xFF, ver);

    /* FFMS_GetLogLevel / FFMS_SetLogLevel: verify log-level round-trip */
    int orig_level = FFMS_GetLogLevel();
    FFMS_SetLogLevel(0);
    int new_level = FFMS_GetLogLevel();
    if (new_level != 0) {
        fprintf(stderr, "FAIL: SetLogLevel(0) did not take effect, got %d\n", new_level);
        return 1;
    }
    FFMS_SetLogLevel(orig_level);

    /* FFMS_CreateIndexer: attempt to create an indexer on a non-existent
       file — this exercises the error-handling path (returns NULL with
       an error message) rather than succeeding, proving the API is
       callable and the library is properly linked. */
    FFMS_ErrorInfo err;
    char errbuf[1024];
    err.BufferSize = sizeof(errbuf);
    err.Buffer = errbuf;

    FFMS_Indexer *indexer = FFMS_CreateIndexer("/dev/null/nonexistent", &err);
    if (indexer != NULL) {
        /* Unexpected — /dev/null/nonexistent should not be openable */
        fprintf(stderr, "FAIL: CreateIndexer unexpectedly succeeded\n");
        return 1;
    }

    printf("CreateIndexer error (expected): %s\n", err.Buffer[0] ? err.Buffer : "(no message)");
    printf("All ffms2 API tests passed.\n");
    return 0;
}
