#include <stdio.h>
#include <zzip/lib.h>

int main(void) {
    const char* version = zzip_version();
    printf("zziplib version: %s\n", version);
    return 0;
}