/*
 * C ABI consumer test for imageflow 2.3.1_rc01.
 *
 * Compiled against the packaged bindings/headers and linked against the
 * packaged libimageflow.so; exercises the stable C ABI on HarmonyOS:
 *   - imageflow_abi_version_major()/minor()
 *   - imageflow_abi_compatible()
 *   - imageflow_context_create()/imageflow_context_destroy()
 *
 * The conan test_package runs this binary with VirtualRunEnv, which puts the
 * package lib dir on LD_LIBRARY_PATH (OHOS ignores DT_RUNPATH).
 */
#include <stdio.h>
#include <stdint.h>

#include <imageflow_default.h>

int main(void) {
    uint32_t major = imageflow_abi_version_major();
    uint32_t minor = imageflow_abi_version_minor();
    printf("imageflow C ABI version %u.%u\n", major, minor);

    if (!imageflow_abi_compatible(major, minor)) {
        printf("FAIL: imageflow_abi_compatible(%u, %u) returned false\n",
               major, minor);
        return 1;
    }
    printf("imageflow_abi_compatible(%u, %u) = true\n", major, minor);

    struct imageflow_context *context = imageflow_context_create(major, minor);
    if (context == NULL) {
        printf("FAIL: imageflow_context_create returned NULL\n");
        return 1;
    }
    printf("imageflow_context_create OK (%p)\n", (void *)context);
    imageflow_context_destroy(context);
    printf("imageflow_context_destroy OK\n");

    printf("C ABI consumer test PASS\n");
    return 0;
}
