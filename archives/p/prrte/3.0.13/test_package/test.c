#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "prte_version.h"

int main(void) {
    int total = 0;
    int passed = 0;

    /* ---- version macros from the packaged prte_version.h ---- */
    total++;
    if (PRTE_VERSION_MAJOR == 3) {
        passed++;
        printf("ASSERT OK: PRTE_VERSION_MAJOR == 3\n");
    } else {
        printf("ASSERT FAIL: PRTE_VERSION_MAJOR == %ld\n", PRTE_VERSION_MAJOR);
    }

    total++;
    if (PRTE_VERSION_MINOR == 0) {
        passed++;
        printf("ASSERT OK: PRTE_VERSION_MINOR == 0\n");
    } else {
        printf("ASSERT FAIL: PRTE_VERSION_MINOR == %ld\n", PRTE_VERSION_MINOR);
    }

    total++;
    if (PRTE_VERSION_RELEASE == 13) {
        passed++;
        printf("ASSERT OK: PRTE_VERSION_RELEASE == 13\n");
    } else {
        printf("ASSERT FAIL: PRTE_VERSION_RELEASE == %ld\n", PRTE_VERSION_RELEASE);
    }

    total++;
    if (PRTE_NUMERIC_VERSION == 0x0003000d) {
        passed++;
        printf("ASSERT OK: PRTE_NUMERIC_VERSION == 0x0003000d\n");
    } else {
        printf("ASSERT FAIL: PRTE_NUMERIC_VERSION == 0x%x\n",
               (unsigned int) PRTE_NUMERIC_VERSION);
    }

    printf("PRTE_TEST_ASSERTIONS: total=%d passed=%d\n", total, passed);
    return (total == passed) ? 0 : 1;
}
