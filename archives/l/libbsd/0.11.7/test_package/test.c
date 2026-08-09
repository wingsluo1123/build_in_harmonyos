#include <stdio.h>
#include <bsd/string.h>
#include <bsd/stdlib.h>

int main(void) {
    /* Use libbsd's strlcpy function */
    char dst[16];
    strlcpy(dst, "hello libbsd", sizeof(dst));
    printf("strlcpy result: %s\n", dst);

    /* Use libbsd's strtonum function */
    const char *errstr = NULL;
    long val = strtonum("42", 1, 100, &errstr);
    if (errstr != NULL) {
        printf("strtonum error: %s\n", errstr);
        return 1;
    }
    printf("strtonum result: %ld\n", val);
    return 0;
}
