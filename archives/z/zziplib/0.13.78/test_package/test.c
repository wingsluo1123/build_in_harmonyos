#include <stdio.h>
#include <zzip/lib.h>

int main(void) {
    const char* version = zzip_version();
    if (version == NULL) {
        fprintf(stderr, "FAIL: zzip_version() returned NULL\n");
        return 1;
    }
    printf("zziplib version: %s\n", version);
    return 0;
}