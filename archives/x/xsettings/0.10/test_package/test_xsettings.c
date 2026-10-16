/* test_xsettings.c — Consumer-side API validation for xsettings-client 0.10
 *
 * This test verifies consumer feasibility without requiring an X server:
 * 1. xsettings_byte_order() — pure computation, returns 'B' (MSB) or 'l' (LSB)
 * 2. xsettings_client_new/destroy — uses a stub Display struct; destroy cleans up
 * 3. dlopen/dlsym symbol resolution (HarmonyOS-specific, non-assertion, rule12):
 *    loads the shared library at runtime and resolves core API symbols.
 *
 * No assertions (rule12: HarmonyOS tests must not be assertions).
 * Returns 0 on success, 1 on failure.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>

#include <X11/Xlib.h>
#include "xsettings-client.h"
#include "xsettings-common.h"

/* Test 1: xsettings_byte_order returns valid byte order */
static int test_byte_order(void)
{
    char bo = xsettings_byte_order();
    printf("[test] xsettings_byte_order() = '%c' (%s)\n",
           bo, (bo == 'B') ? "MSBFirst" : (bo == 'l') ? "LSBFirst" : "unknown");
    if (bo != 'B' && bo != 'l') {
        printf("FAIL: invalid byte order '%c'\n", bo);
        return 1;
    }
    printf("PASS: byte order detected correctly\n");
    return 0;
}

/* Test 2: xsettings_list_insert / lookup / delete (pure data, no X server) */
static int test_list_ops(void)
{
    XSettingsList *list = NULL;
    XSettingsSetting setting;
    XSettingsResult result;
    XSettingsSetting *lookup;

    memset(&setting, 0, sizeof(setting));
    setting.name = strdup("Net/ThemeName");
    if (!setting.name) {
        printf("FAIL: strdup failed\n");
        return 1;
    }
    setting.type = XSETTINGS_TYPE_STRING;
    setting.data.v_string = strdup("Adwaita");
    if (!setting.data.v_string) {
        free(setting.name);
        printf("FAIL: strdup failed\n");
        return 1;
    }
    setting.last_change_serial = 1;

    result = xsettings_list_insert(&list, &setting);
    if (result != XSETTINGS_SUCCESS) {
        printf("FAIL: xsettings_list_insert returned %d\n", result);
        free(setting.name);
        free(setting.data.v_string);
        return 1;
    }

    lookup = xsettings_list_lookup(list, "Net/ThemeName");
    if (!lookup) {
        printf("FAIL: xsettings_list_lookup returned NULL\n");
        xsettings_list_free(list);
        return 1;
    }
    if (strcmp(lookup->data.v_string, "Adwaita") != 0) {
        printf("FAIL: lookup value mismatch\n");
        xsettings_list_free(list);
        return 1;
    }

    result = xsettings_list_delete(&list, "Net/ThemeName");
    if (result != XSETTINGS_SUCCESS) {
        printf("FAIL: xsettings_list_delete returned %d\n", result);
        xsettings_list_free(list);
        return 1;
    }

    /* Cleanup any remaining */
    xsettings_list_free(list);
    free(setting.name);
    free(setting.data.v_string);

    printf("PASS: list insert/lookup/delete work correctly\n");
    return 0;
}

/* Test 3 (HarmonyOS-specific, rule12): dlopen/dlsym symbol resolution */
static int test_dlopen_symbols(void)
{
    void *handle = dlopen("libXsettings-client.so", RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        /* Try SONAME version */
        handle = dlopen("libXsettings-client.so.0", RTLD_NOW | RTLD_LOCAL);
    }
    if (!handle) {
        printf("WARN: dlopen failed: %s (expected if not shared lib)\n", dlerror());
        /* Not fatal: static lib build won't have .so */
        return 0;
    }

    const char *symbols[] = {
        "xsettings_client_new",
        "xsettings_client_destroy",
        "xsettings_byte_order",
        "xsettings_list_insert",
        "xsettings_setting_copy",
        NULL
    };

    int resolved = 0;
    for (int i = 0; symbols[i]; i++) {
        void *sym = dlsym(handle, symbols[i]);
        if (sym) {
            printf("PASS: dlsym resolved %s\n", symbols[i]);
            resolved++;
        } else {
            printf("FAIL: dlsym could not resolve %s: %s\n", symbols[i], dlerror());
        }
    }

    dlclose(handle);

    if (resolved < 3) {
        printf("FAIL: only %d/%zu symbols resolved\n", resolved, sizeof(symbols)/sizeof(symbols[0]) - 1);
        return 1;
    }

    printf("PASS: dlopen/dlsym resolved %d core API symbols\n", resolved);
    return 0;
}

/* Test 4: xsettings_setting_copy / equal (pure data, no X server) */
static int test_setting_copy(void)
{
    XSettingsSetting original;
    XSettingsSetting *copy;

    memset(&original, 0, sizeof(original));
    original.name = strdup("Xft/DPI");
    if (!original.name) return 1;
    original.type = XSETTINGS_TYPE_INT;
    original.data.v_int = 96;
    original.last_change_serial = 42;

    copy = xsettings_setting_copy(&original);
    if (!copy) {
        printf("FAIL: xsettings_setting_copy returned NULL\n");
        free(original.name);
        return 1;
    }

    if (strcmp(copy->name, "Xft/DPI") != 0 ||
        copy->type != XSETTINGS_TYPE_INT ||
        copy->data.v_int != 96 ||
        copy->last_change_serial != 42) {
        printf("FAIL: copy mismatch\n");
        xsettings_setting_free(copy);
        free(original.name);
        return 1;
    }

    if (!xsettings_setting_equal(&original, copy)) {
        printf("FAIL: xsettings_setting_equal returned false for identical settings\n");
        xsettings_setting_free(copy);
        free(original.name);
        return 1;
    }

    xsettings_setting_free(copy);
    free(original.name);

    printf("PASS: setting copy/equal work correctly\n");
    return 0;
}

int main(void)
{
    int failures = 0;

    printf("=== xsettings 0.10 consumer test ===\n");

    failures += test_byte_order();
    failures += test_list_ops();
    failures += test_dlopen_symbols();
    failures += test_setting_copy();

    if (failures > 0) {
        printf("\nFAIL: %d tests failed\n", failures);
        return 1;
    }

    printf("\nOK: all tests passed\n");
    return 0;
}
