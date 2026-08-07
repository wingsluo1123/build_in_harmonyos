// test.c — perf 6.6.9 test package source
// R34: This test exercises the perf binary by running perf --version
// and checking the exit code. perf is a CLI tool, so we use system().

#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    int rc = system("perf --version");
    if (rc != 0) {
        fprintf(stderr, "FAIL: perf --version returned %d\n", rc);
        return 1;
    }
    printf("PASS: perf --version executed successfully\n");
    return 0;
}
