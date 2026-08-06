#include <libpsl.h>
#include <stdio.h>

int main(void) {
    /* Test: load built-in PSL data and verify it works */
    const psl_t *psl = psl_builtin();
    if (psl == NULL) {
        fprintf(stderr, "FAIL: psl_builtin() returned NULL\n");
        return 1;
    }
    /* Test: verify 'com' is recognized as a public suffix */
    if (psl_is_public_suffix(psl, "com") == 0) {
        fprintf(stderr, "FAIL: 'com' not recognized as public suffix\n");
        return 1;
    }
    printf("OK: libpsl 0.21.5 test passed\n");
    return 0;
}
