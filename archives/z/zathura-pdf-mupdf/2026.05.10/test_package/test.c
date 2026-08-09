#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>

/* Test: dlopen the plugin .so and verify the zathura_plugin_67 symbol exists.
 * This is a meaningful test (R34) that verifies the package's primary artifact
 * is a valid shared module with the expected plugin definition symbol.
 * The symbol name is derived from ZATHURA_API_VERSION=6, ZATHURA_ABI_VERSION=7. */
int main(void) {
    const char *so_path = getenv("PLUGIN_SO_PATH");
    if (!so_path) {
        fprintf(stderr, "FAIL: PLUGIN_SO_PATH not set\n");
        return 1;
    }

    void *handle = dlopen(so_path, RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        fprintf(stderr, "FAIL: dlopen(%s): %s\n", so_path, dlerror());
        return 1;
    }

    /* ZATHURA_PLUGIN_DEFINITION_SYMBOL = JOIN(zathura_plugin, JOIN(6, 7))
     * = zathura_plugin_67 */
    void *sym = dlsym(handle, "zathura_plugin_67");
    if (!sym) {
        fprintf(stderr, "FAIL: dlsym(zathura_plugin_67): %s\n", dlerror());
        dlclose(handle);
        return 1;
    }

    printf("test zathura-pdf-mupdf 2026.05.10: OK (plugin symbol zathura_plugin_67 found)\n");
    dlclose(handle);
    return 0;
}
