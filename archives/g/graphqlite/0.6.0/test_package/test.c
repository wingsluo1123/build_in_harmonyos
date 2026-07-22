/*
 * R34 test for graphqlite 0.6.0 — SQLite extension loadability.
 *
 * graphqlite is an SQLite extension shipped as a .so loaded at runtime
 * by sqlite3 (sqlite3_load_extension). The canonical entry symbol that
 * SQLite looks for is `sqlite3_graphqlite_init`. This test:
 *   1. dlopen()s the .so (tries libgraphqlite.so then graphqlite.so)
 *   2. dlsym()s sqlite3_graphqlite_init — the extension init entry point
 *      that SQLite invokes when loading the extension
 *   3. fails explicitly if either step fails (no false "OK")
 *
 * This exercises real symbol resolution: a broken, stripped, or
 * mis-exported .so will be caught here, not silently pass.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>

int main(void) {
    /* Step 1: load the shared library */
    void *handle = dlopen("libgraphqlite.so", RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        /* Retry without the lib prefix (Makefile may produce graphqlite.so) */
        handle = dlopen("graphqlite.so", RTLD_NOW | RTLD_LOCAL);
    }
    if (!handle) {
        fprintf(stderr, "FAIL: dlopen failed: %s\n", dlerror());
        return 1;
    }
    printf("PASS: extension loaded\n");

    /* Step 2: verify the extension init entry point exists.
     * SQLite extensions export sqlite3_<name>_init; for graphqlite the
     * canonical symbol is sqlite3_graphqlite_init. A stripped or
     * mis-exported .so would miss this symbol and fail here. */
    dlerror(); /* clear any pending error */
    void (*init)(void) = (void (*)(void))dlsym(handle, "sqlite3_graphqlite_init");
    const char *sym_err = dlerror();
    if (sym_err || !init) {
        fprintf(stderr, "FAIL: dlsym(sqlite3_graphqlite_init) failed: %s\n",
                sym_err ? sym_err : "(symbol is NULL)");
        dlclose(handle);
        return 1;
    }
    printf("PASS: sqlite3_graphqlite_init entry symbol resolved\n");

    dlclose(handle);
    printf("graphqlite 0.6.0: all tests PASSED\n");
    return 0;
}
