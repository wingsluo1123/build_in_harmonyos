#include <stdio.h>
#include <stdlib.h>

int main(void) {
    // Test that spek-cli runs and produces help output
    int rc = system("spek-cli --help > /dev/null 2>&1");
    if (rc == 0) {
        printf("spek-cli 0.8.5: OK\n");
    } else {
        printf("spek-cli 0.8.5: FAIL (exit %d)\n", rc);
    }
    return rc;
}
