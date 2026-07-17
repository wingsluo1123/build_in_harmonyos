#include <zstd.h>
#include <dlfcn.h>
#include <stdio.h>
#ifndef TARGET_SO
#define TARGET_SO "libzstd.so"
#endif
int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    if (!dlsym(h, "ZSTD_versionNumber")) { fprintf(stderr, "symbol ZSTD_versionNumber not found: %s\n", dlerror()); dlclose(h); return 1; }
    printf("zstd: dlopen %s ok\n", TARGET_SO);
    dlclose(h);
    return 0;
}