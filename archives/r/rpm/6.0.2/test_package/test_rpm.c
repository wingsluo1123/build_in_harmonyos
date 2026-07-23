/* test_rpm.c - Consumer test: link against librpm and call rpmReadConfigFiles */
#include <rpm/rpmlib.h>
#include <stdio.h>

int main(void) {
    /* Verify the library is linkable and the API is callable */
    rpmReadConfigFiles(NULL, NULL);
    /* Print version constant to verify linkage */
    printf("rpm version: %s\n", RPMVERSION);
    return 0;
}
