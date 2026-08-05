/* test.c — abiword-plugin-docbook L1 smoke test
 *
 * Loads the docbook plugin .so via dlopen and verifies the AbiWord plugin
 * ABI symbols (abi_plugin_register/unregister/supports_version) are exported
 * and that abi_plugin_supports_version(3,0,0) returns 1.
 *
 * Compile with -DTARGET_SO=<path-to-docbook.so> passed from CMake.
 */
#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>

typedef int (*supports_version_fn)(unsigned, unsigned, unsigned);
typedef int (*register_fn)(void);
typedef int (*unregister_fn)(void);

int main(void) {
    const char *so_path = TARGET_SO;
    if (!so_path || so_path[0] == '\0') {
        fprintf(stderr, "FAIL: TARGET_SO not defined at compile time\n");
        return 2;
    }

    void *handle = dlopen(so_path, RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        fprintf(stderr, "FAIL: dlopen(%s) failed: %s\n", so_path, dlerror());
        return 1;
    }
    printf("[ok] dlopen(%s) succeeded\n", so_path);

    int failures = 0;

    /* abi_plugin_supports_version must exist and return 1 for ABI 3.0.0 */
    supports_version_fn supports_version =
        (supports_version_fn)dlsym(handle, "abi_plugin_supports_version");
    if (!supports_version) {
        fprintf(stderr, "FAIL: abi_plugin_supports_version symbol not found\n");
        failures++;
    } else {
        int rv = supports_version(3, 0, 0);
        printf("[ok] abi_plugin_supports_version(3,0,0) returned %d\n", rv);
        if (rv != 1) {
            fprintf(stderr, "FAIL: expected return value 1, got %d\n", rv);
            failures++;
        }
    }

    /* abi_plugin_register must exist */
    register_fn reg = (register_fn)dlsym(handle, "abi_plugin_register");
    if (!reg) {
        fprintf(stderr, "FAIL: abi_plugin_register symbol not found\n");
        failures++;
    } else {
        printf("[ok] abi_plugin_register symbol found\n");
    }

    /* abi_plugin_unregister must exist */
    unregister_fn unreg = (unregister_fn)dlsym(handle, "abi_plugin_unregister");
    if (!unreg) {
        fprintf(stderr, "FAIL: abi_plugin_unregister symbol not found\n");
        failures++;
    } else {
        printf("[ok] abi_plugin_unregister symbol found\n");
    }

    dlclose(handle);

    if (failures > 0) {
        fprintf(stderr, "FAIL: %d symbol check(s) failed\n", failures);
        return 1;
    }
    printf("Smoke test PASSED.\n");
    return 0;
}
