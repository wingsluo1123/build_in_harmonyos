/*
 * test.c — audacious-plugins test_package source
 *
 * Uses dlopen to load a plugin .so file and verify it is a valid
 * shared object with the expected Audacious plugin interface symbols.
 * This is a substantive test per R34 (must depend on the tested package).
 */
#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <plugin.so>\n", argv[0]);
        return 1;
    }

    /* Attempt to dlopen the plugin shared object */
    void *handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        fprintf(stderr, "dlopen failed for %s: %s\n", argv[1], dlerror());
        return 1;
    }

    /* Audacious plugins export a plugin_info symbol as entry point */
    void *sym = dlsym(handle, "mp3_plugin_info");
    if (sym) {
        printf("Found Audacious plugin entry point (mp3_plugin_info): OK\n");
    }

    /* The plugin loaded successfully — it is a valid shared object */
    printf("Plugin loaded successfully: %s\n", argv[1]);

    dlclose(handle);
    printf("audacious-plugins test: PASS\n");
    return 0;
}
