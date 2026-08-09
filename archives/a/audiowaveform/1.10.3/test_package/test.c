/* R34: Test source file that executes the audiowaveform binary.
 * This test calls system() to run the audiowaveform binary,
 * verifying that the package provides a working executable.
 */
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int ret = system("audiowaveform --help > /dev/null 2>&1");
    if (ret != 0) {
        fprintf(stderr, "FAIL: audiowaveform binary not working (exit code %d)\n", ret);
        return 1;
    }
    printf("PASS: audiowaveform binary executed successfully\n");
    return 0;
}
