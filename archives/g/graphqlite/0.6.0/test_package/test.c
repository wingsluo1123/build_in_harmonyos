#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>

int main(void) {
    /* Test 1: Verify the extension library exists and is loadable */
    void *handle = dlopen("libgraphqlite.so", RTLD_LAZY | RTLD_LOCAL);
    if (!handle) {
        /* Try without lib prefix */
        handle = dlopen("graphqlite.so", RTLD_LAZY | RTLD_LOCAL);
    }
    if (!handle) {
        fprintf(stderr, "FAIL: could not load graphqlite.so: %s\n", dlerror());
        return 1;
    }
    printf("graphqlite 0.6.0: extension loaded successfully\n");
    dlclose(handle);
    return 0;
}