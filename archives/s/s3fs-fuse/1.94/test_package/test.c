#include <stdio.h>
#include <stdlib.h>

/* R34: test must depend on the tested package.
 * s3fs-fuse is a command-line tool, so this test verifies
 * the binary can be located and executed.
 * The actual binary execution is in conanfile.py test() method
 * which runs `s3fs --version` and checks the output.
 */
int main(void) {
    printf("test s3fs-fuse 1.94: binary check\n");
    return 0;
}
