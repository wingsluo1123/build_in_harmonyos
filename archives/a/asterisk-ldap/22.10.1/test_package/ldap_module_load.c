/* test_package/ldap_module_load.c — HarmonyOS dynamic load test.
 *
 * The Asterisk module ABI works like this: `AST_MODULE_INFO()` in
 * res_config_ldap.c defines a `static struct ast_module_info __mod_info` plus a
 * constructor (`__reg_module`) that calls `ast_module_register(&__mod_info)`.
 * The Asterisk loader only has to dlopen() the shared object — the constructor
 * registers the module. This driver reproduces exactly that boundary:
 *
 *   1. stub definitions for the Asterisk core API symbols (generated at test
 *      build time from the module's own undefined symbol list) are linked into
 *      this executable with -rdynamic, so the module resolves them from the
 *      process image, just as it would from the real asterisk binary;
 *   2. dlopen(path, RTLD_NOW) — eager binding, so success proves every
 *      dependency of the OHOS-built module (libldap.so.2, liblber.so.2, libc)
 *      resolves through the OHOS loader;
 *   3. assert the constructor ran exactly once and produced a valid
 *      `struct ast_module_info` for res_config_ldap.
 *
 * struct ast_module_info field offsets (include/asterisk/module.h, LP64):
 *   0 self, 8 load, 16 reload, 24 unload, 32 name, 40 description, 48 key.
 */
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>

/* provided by the generated stub object */
extern void *__ohos_test_module_info;
extern int __ohos_test_register_calls;

static const size_t OFF_LOAD = 8;
static const size_t OFF_UNLOAD = 24;
static const size_t OFF_NAME = 32;
static const size_t OFF_DESC = 40;
static const size_t OFF_KEY = 48;

static void *read_ptr(unsigned char *base, size_t off)
{
    void *value;
    memcpy(&value, base + off, sizeof(value));
    return value;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        printf("usage: %s <res_config_ldap.so>\n", argv[0]);
        return 10;
    }

    void *handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (NULL == handle) {
        printf("[fail] dlopen(RTLD_NOW) failed: %s\n", dlerror());
        return 1;
    }
    printf("[ok]   dlopen(RTLD_NOW) succeeded — all shared libraries resolved\n");

    if (__ohos_test_register_calls != 1) {
        printf("[fail] ast_module_register called %d time(s), expected 1\n",
               __ohos_test_register_calls);
        return 2;
    }
    printf("[ok]   module constructor called ast_module_register exactly once\n");

    unsigned char *info = (unsigned char *)__ohos_test_module_info;
    if (NULL == info) {
        printf("[fail] ast_module_register received a NULL info pointer\n");
        return 3;
    }

    const char *name = (const char *)read_ptr(info, OFF_NAME);
    const char *desc = (const char *)read_ptr(info, OFF_DESC);
    const char *key = (const char *)read_ptr(info, OFF_KEY);
    void *load = read_ptr(info, OFF_LOAD);
    void *unload = read_ptr(info, OFF_UNLOAD);

    if (NULL == name || 0 != strcmp(name, "res_config_ldap")) {
        printf("[fail] module name is '%s', expected 'res_config_ldap'\n",
               name ? name : "()");
        return 4;
    }
    printf("[ok]   registered module name = '%s'\n", name);

    if (NULL == desc || '\0' == desc[0]) {
        printf("[fail] module description is empty\n");
        return 5;
    }
    printf("[ok]   module description = '%s'\n", desc);

    if (NULL == key || NULL == load || NULL == unload) {
        printf("[fail] incomplete module info (key=%p load=%p unload=%p)\n",
               (void *)key, load, unload);
        return 6;
    }
    printf("[ok]   load/unload entry points and license key present\n");

    printf("DYNAMIC LOAD TEST PASSED\n");
    dlclose(handle);
    return 0;
}
