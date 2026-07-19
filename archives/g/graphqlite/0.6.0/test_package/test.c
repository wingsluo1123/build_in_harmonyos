#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>

/* SQLite extension entry point signature */
typedef int (*sqlite3_ext_init_fn)(void *, char **, void *);

int main(void) {
    int failures = 0;

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
    printf("PASS: graphqlite.so loaded successfully\n");

    /* Test 2: Verify the SQLite extension entry point symbol exists */
    sqlite3_ext_init_fn init_fn = (sqlite3_ext_init_fn)dlsym(handle, "sqlite3_graphqlite_init");
    if (!init_fn) {
        fprintf(stderr, "FAIL: sqlite3_graphqlite_init symbol not found: %s\n", dlerror());
        failures++;
    } else {
        printf("PASS: sqlite3_graphqlite_init found at %p\n", (void *)init_fn);
    }

    /* Test 3: Verify other key API symbols are present */
    if (!dlsym(handle, "cypher_parse_query")) {
        fprintf(stderr, "FAIL: cypher_parse_query symbol not found: %s\n", dlerror());
        failures++;
    } else {
        printf("PASS: cypher_parse_query symbol found\n");
    }

    if (!dlsym(handle, "cypher_executor_create")) {
        fprintf(stderr, "FAIL: cypher_executor_create symbol not found: %s\n", dlerror());
        failures++;
    } else {
        printf("PASS: cypher_executor_create symbol found\n");
    }

    if (!dlsym(handle, "cypher_free_result")) {
        fprintf(stderr, "FAIL: cypher_free_result symbol not found: %s\n", dlerror());
        failures++;
    } else {
        printf("PASS: cypher_free_result symbol found\n");
    }

    dlclose(handle);

    if (failures > 0) {
        printf("graphqlite 0.6.0: %d test(s) FAILED\n", failures);
        return 1;
    }
    printf("graphqlite 0.6.0: all tests PASSED\n");
    return 0;
}