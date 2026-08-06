#include <stdio.h>

/* Minimal test stub — actual verification is done in conanfile.py test()
 * which runs `netdata -v` to check the installed binary.
 * This file exists to satisfy CMake's requirement for a build target. */
int main(void) {
    printf("test netdata 1.47.5: OK\n");
    return 0;
}
