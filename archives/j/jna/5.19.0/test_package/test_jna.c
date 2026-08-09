#include <stdio.h>
#include <dlfcn.h>

/* Test: load libjnidispatch.so and verify JNI exports are present.
 * This is a smoke test that verifies the native library is valid
 * without requiring a JVM runtime.
 */
int main(void) {
    void *handle = dlopen("libjnidispatch.so", RTLD_LAZY);
    if (!handle) {
        fprintf(stderr, "FAIL: cannot load libjnidispatch.so: %s\n", dlerror());
        return 1;
    }

    /* Check key JNI function exports */
    const char *symbols[] = {
        "Java_com_sun_jna_Native_initIDs",
        "Java_com_sun_jna_Native_malloc",
        "Java_com_sun_jna_Native_free",
        "Java_com_sun_jna_Native_open",
        "Java_com_sun_jna_Native_close",
        "Java_com_sun_jna_Native_findSymbol",
        "Java_com_sun_jna_Native_getByte",
        "Java_com_sun_jna_Native_setByte",
        "Java_com_sun_jna_Native_invokePointer",
        "Java_com_sun_jna_Native_invokeInt",
    };
    int nsyms = sizeof(symbols) / sizeof(symbols[0]);

    for (int i = 0; i < nsyms; i++) {
        void *sym = dlsym(handle, symbols[i]);
        if (!sym) {
            fprintf(stderr, "FAIL: %s not found: %s\n", symbols[i], dlerror());
            dlclose(handle);
            return 1;
        }
    }

    dlclose(handle);
    printf("test jna 5.19.0: OK (all %d JNI exports verified)\n", nsyms);
    return 0;
}
