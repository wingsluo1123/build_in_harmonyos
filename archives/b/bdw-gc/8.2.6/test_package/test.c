#include <stdio.h>
#include "gc.h"

int main(void) {
    GC_INIT();
    printf("gc version: %s\n", GC_get_version());
    void *p = GC_MALLOC(64);
    if (p) { printf("gc malloc: OK\n"); }
    return 0;
}
