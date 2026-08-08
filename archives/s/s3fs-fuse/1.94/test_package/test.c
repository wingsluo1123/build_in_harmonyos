#include <stdio.h>
#include <stdlib.h>

/* R34: test must actually depend on the tested package.
 * s3fs-fuse is a command-line tool, so this test executes
 * the s3fs binary via system() and checks the exit code.
 */
int main(void) {
    int ret = system("s3fs --version");
    return (ret == 0) ? 0 : 1;
}
