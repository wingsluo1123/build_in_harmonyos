#include <s2n.h>
#include <stdio.h>

int main(void) {
    if (s2n_init() != 0) {
        fprintf(stderr, "FAIL: s2n_init returned error: %s\n", s2n_strerror(s2n_errno, "EN"));
        return 1;
    }
    printf("PASS: s2n_init succeeded\n");

    if (s2n_cleanup() != 0) {
        fprintf(stderr, "FAIL: s2n_cleanup returned error\n");
        return 1;
    }
    printf("PASS: s2n 1.7.3 test completed successfully\n");
    return 0;
}
