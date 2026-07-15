#include <fontconfig/fontconfig.h>
#include <dlfcn.h>
#include <stdio.h>
#ifndef TARGET_SO
#define TARGET_SO "libfontconfig.so"
#endif
int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    printf("fontconfig: dlopen %s ok\n", TARGET_SO);

    /* R34: 调用 fontconfig API 验证库功能可用 */
    int ver = FcGetVersion();
    if (ver <= 0) { fprintf(stderr, "FcGetVersion failed: %d\n", ver); dlclose(h); return 1; }
    printf("fontconfig: FcGetVersion = %d\n", ver);

    dlclose(h);
    return 0;
}
