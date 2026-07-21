#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <slang.h>

int main(void) {
    /* Initialize the S-Lang library */
    if (SLang_init_all() != 0) {
        fprintf(stderr, "Failed to initialize S-Lang library\n");
        return 1;
    }

    /* Verify the version string */
    const char *ver_str = SLang_Version_String;
    int ver_num = SLang_Version;

    printf("S-Lang version string: %s\n", ver_str ? ver_str : "(null)");
    printf("S-Lang version number: %d\n", ver_num);

    /* Check that version matches expected (2.3.3 = 20303) */
    if (ver_num != SLANG_VERSION) {
        fprintf(stderr, "Version mismatch: got %d, expected %d\n",
                ver_num, SLANG_VERSION);
        return 1;
    }

    /* Check version string */
    if (!ver_str || strcmp(ver_str, SLANG_VERSION_STRING) != 0) {
        fprintf(stderr, "Version string mismatch: got '%s', expected '%s'\n",
                ver_str ? ver_str : "(null)", SLANG_VERSION_STRING);
        return 1;
    }

    printf("S-Lang API test: PASS\n");
    SLang_reset_tty();
    return 0;
}
