/* R34: test_package must call actual ICU API, not just print strings.
 * Symbol renaming is enabled by default (ICU compiled with version suffix).
 * Headers apply renaming macros consistently to declarations and calls. */

#include <stdio.h>
#include <string.h>
#include <unicode/utypes.h>
#include <unicode/uclean.h>   /* u_init() declaration */
#include <unicode/uchar.h>    /* u_isalpha() declaration */
#include <unicode/ustring.h>  /* u_strlen() declaration */

int main(void) {
    UErrorCode status = U_ZERO_ERROR;

    /* Initialize ICU */
    u_init(&status);
    if (U_FAILURE(status)) {
        fprintf(stderr, "u_init() failed: %s\n", u_errorName(status));
        return 1;
    }

    /* Test u_errorName() API */
    const char *err_name = u_errorName(U_ZERO_ERROR);
    if (strcmp(err_name, "U_ZERO_ERROR") != 0) {
        fprintf(stderr, "u_errorName(U_ZERO_ERROR) returned unexpected: %s\n", err_name);
        return 1;
    }

    /* Test u_strlen() API */
    const UChar str[] = {0x0048, 0x0065, 0x006C, 0x006C, 0x006F, 0x0000}; /* "Hello" */
    int32_t len = u_strlen(str);
    if (len != 5) {
        fprintf(stderr, "u_strlen returned %d, expected 5\n", len);
        return 1;
    }

    /* Test u_isalpha() API */
    if (!u_isalpha(0x0041)) { /* 'A' */
        fprintf(stderr, "u_isalpha('A') returned false\n");
        return 1;
    }

    printf("ICU test passed: u_init OK, u_errorName OK, u_strlen OK, u_isalpha OK\n");
    return 0;
}
