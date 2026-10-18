#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>

/*
 * OHOS-specific runtime test: verify the shared library can be loaded
 * at runtime via dlopen. This ensures SONAME is correct and all
 * transitive dependencies (zlib, libyaml) are resolvable.
 * This is NOT an assertion test — it tests the consumer's ability
 * to load the library dynamically on the OHOS platform.
 */
int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <path-to-libubootenv.so>\n", argv[0]);
        return 1;
    }

    const char *libpath = argv[1];
    printf("Loading shared library: %s\n", libpath);

    void *handle = dlopen(libpath, RTLD_NOW);
    if (!handle) {
        fprintf(stderr, "FAIL: dlopen failed: %s\n", dlerror());
        return 1;
    }

    /* Resolve key symbols */
    void *ver_fn = dlsym(handle, "libuboot_version_info");
    void *init_fn = dlsym(handle, "libuboot_initialize");
    void *exit_fn = dlsym(handle, "libuboot_exit");
    void *set_fn = dlsym(handle, "libuboot_set_env");
    void *get_fn = dlsym(handle, "libuboot_get_env");

    if (!ver_fn || !init_fn || !exit_fn || !set_fn || !get_fn) {
        fprintf(stderr, "FAIL: could not resolve all symbols\n");
        dlclose(handle);
        return 1;
    }

    printf("OK: all key symbols resolved\n");

    /* Exercise via function pointer */
    const struct {
        const char *version;
        unsigned int version_num;
    } *(*version_info)(void) = ver_fn;

    /* Note: we can't easily call the functions without the proper struct
     * definition, but symbol resolution + dlopen success proves the
     * library is loadable and has proper SONAME linkage.
     */

    dlclose(handle);
    printf("OK: dlclose succeeded\n");
    return 0;
}
