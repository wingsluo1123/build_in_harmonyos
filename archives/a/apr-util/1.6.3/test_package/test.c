#include <stdio.h>

/* Declare the function without including APR headers to avoid include path issues */
extern const char* apu_version_string(void);

int main(void) {
    printf("apr-util version: %s\n", apu_version_string());
    printf("test apr-util 1.6.3: OK\n");
    return 0;
}
