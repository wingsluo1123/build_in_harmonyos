#include <dlfcn.h>
#include <stdio.h>
#ifndef TARGET_SO
#define TARGET_SO "libXfont2.so"
#endif
int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    void *sym = dlsym(h, "xfont2_make_font_pattern_cache");
    if (!sym) { fprintf(stderr, "dlsym xfont2_make_font_pattern_cache failed: %s\n", dlerror()); dlclose(h); return 2; }
    printf("libxfont2: dlopen %s ok, xfont2_make_font_pattern_cache resolved\n", TARGET_SO);
    dlclose(h);
    return 0;
}
