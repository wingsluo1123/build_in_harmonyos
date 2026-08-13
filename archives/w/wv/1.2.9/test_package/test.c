#include <stdio.h>
#include <wv.h>

int main(void) {
    printf("wv version: %s\n", wv_version);
    return wv_version[0] == '\0';
}
