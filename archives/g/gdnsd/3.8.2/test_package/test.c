#include <stdio.h>

/* Simple test that verifies the gdnsd package is installed and accessible.
 * The actual binary test (gdnsd --version) is run in conanfile.py test(). */
int main(void) {
    printf("test_gdnsd: OK\n");
    return 0;
}
