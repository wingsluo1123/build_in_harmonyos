#include <gd.h>
#include <dlfcn.h>
#include <stdio.h>
#ifndef TARGET_SO
#define TARGET_SO "libgd.so"
#endif
int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    printf("libgd: dlopen %s ok\n", TARGET_SO);
    gdImagePtr (*create)(int, int);
    void (*destroy)(gdImagePtr);
    *(void**)(&create) = dlsym(h, "gdImageCreate");
    *(void**)(&destroy) = dlsym(h, "gdImageDestroy");
    if (!create || !destroy) { dlclose(h); return 1; }
    gdImagePtr im = create(1, 1);
    if (!im) { dlclose(h); return 1; }
    printf("libgd: gdImageCreate(1,1) ok\n");
    destroy(im);
    printf("libgd: gdImageDestroy ok\n");
    dlclose(h);
    printf("test libgd 2.3.3: OK\n");
    return 0;
}
