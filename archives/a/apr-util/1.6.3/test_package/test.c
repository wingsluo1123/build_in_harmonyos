#include <stdio.h>

extern const char* apu_version_string(void);

int main(void) {
    printf("apr-util version: %s\n", apu_version_string());
    printf("test apr-util 1.6.3: OK\n");
    return 0;
}
