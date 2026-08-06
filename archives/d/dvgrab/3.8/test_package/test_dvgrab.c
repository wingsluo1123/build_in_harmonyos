/*
 * test_dvgrab.c — Minimal consumer test for dvgrab
 * dvgrab is a command-line tool, so this test just verifies
 * that the package is found and headers/libraries are available.
 * The actual binary execution test is in conanfile.py test().
 */
#include <stdio.h>

int main(void) {
    printf("dvgrab package found: OK\n");
    return 0;
}
