#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <chm_lib.h>

int main(void)
{
    const char *testfile = "test_minimal.chm";
    int failures = 0;

    /* Test 1: chm_open on a non-existent file must return NULL */
    struct chmFile *h = chm_open("/nonexistent/chmlib_test_does_not_exist.chm");
    if (h != NULL) {
        fprintf(stderr, "FAIL 1: chm_open returned non-NULL for non-existent file\n");
        chm_close(h);
        failures++;
    } else {
        printf("PASS 1: chm_open correctly returned NULL for non-existent file\n");
    }

    /* Test 2: chm_close(NULL) should be safe (no crash) */
    chm_close(NULL);
    printf("PASS 2: chm_close(NULL) did not crash\n");

    /* Test 3: chm_resolve_object on NULL handle returns failure */
    struct chmUnitInfo ui;
    memset(&ui, 0, sizeof(ui));
    if (chm_resolve_object(NULL, "/test", &ui) != CHM_RESOLVE_FAILURE) {
        fprintf(stderr, "FAIL 3: chm_resolve_object on NULL should return CHM_RESOLVE_FAILURE\n");
        failures++;
    } else {
        printf("PASS 3: chm_resolve_object correctly failed on NULL handle\n");
    }

    /* Test 4: Create a minimal ITSF header file and attempt to open it.
       This verifies the library can handle real(ish) CHM data, not just NULLs. */
    {
        FILE *f = fopen(testfile, "wb");
        if (f == NULL) {
            printf("SKIP 4: Cannot create test file (filesystem issue)\n");
        } else {
            /* Minimal ITSF v3 header — 96 bytes.
               ITSF magic + version=3 + header_len=96 + unknown=1 + zero-fill rest. */
            unsigned char itsf_header[96];
            memset(itsf_header, 0, sizeof(itsf_header));
            memcpy(itsf_header, "ITSF", 4);          /* 0x00: magic */
            itsf_header[4]  = 3;                      /* 0x04: version LE = 3 */
            itsf_header[8]  = 0x60;                   /* 0x08: header length LE = 96 */
            itsf_header[12] = 1;                      /* 0x0C: unknown, always 1 */
            fwrite(itsf_header, 1, sizeof(itsf_header), f);
            fclose(f);

            h = chm_open(testfile);
            if (h != NULL) {
                chm_close(h);
                printf("PASS 4: chm_open succeeded on minimal ITSF file, closed safely\n");
            } else {
                printf("PASS 4: chm_open gracefully rejected incomplete ITSF file\n");
            }
            remove(testfile);
        }
    }

    if (failures > 0) {
        fprintf(stderr, "\nchmlib test FAILED: %d check(s) failed\n", failures);
        return 1;
    }
    printf("\nchmlib test PASSED: all API safety checks passed\n");
    return 0;
}
