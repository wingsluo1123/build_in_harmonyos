#include <dlfcn.h>
#include <stdio.h>
#include <sys/stat.h>

static int check_file(const char *root, const char *relative, const char *label)
{
    char path[1024];
    struct stat st;
    snprintf(path, sizeof(path), "%s/%s", root, relative);
    if (stat(path, &st) != 0) {
        printf("FAIL: %s missing: %s\n", label, path);
        return 1;
    }
    printf("PASS: %s: %s\n", label, path);
    return 0;
}

static int check_symbol(void *handle, const char *name)
{
    dlerror();
    void *symbol = dlsym(handle, name);
    if (!symbol) {
        const char *error = dlerror();
        printf("FAIL: dlsym(%s): %s\n", name, error ? error : "null symbol");
        return 1;
    }
    printf("PASS: dlsym(%s) -> %p\n", name, symbol);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc != 3) {
        fprintf(stderr, "usage: %s <package_root> <framework_root>\n", argv[0]);
        return 2;
    }

    const char *package_root = argv[1];
    const char *framework_root = argv[2];
    int failures = 0;

    failures |= check_file(package_root, "bin/verify-proxy-tool", "CLI");
    failures |= check_file(package_root, "lib/lcmaps/liblcmaps_verify_proxy.so", "module");
    failures |= check_file(package_root, "lib/lcmaps/lcmaps_verify_proxy.mod", "install entry");
    failures |= check_file(framework_root, "lib/liblcmaps_without_gsi.so", "framework");

    char module[1024];
    snprintf(module, sizeof(module), "%s/lib/lcmaps/lcmaps_verify_proxy.mod", package_root);
    dlerror();
    void *handle = dlopen(module, RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        const char *error = dlerror();
        printf("FAIL: dlopen %s: %s\n", module, error ? error : "unknown error");
        return 1;
    }
    printf("PASS: dlopen %s\n", module);

    const char *symbols[] = {
        "plugin_initialize",
        "plugin_introspect",
        "plugin_run",
        "plugin_verify",
        "plugin_terminate",
    };
    for (size_t i = 0; i < sizeof(symbols) / sizeof(symbols[0]); ++i)
        failures |= check_symbol(handle, symbols[i]);

    if (dlclose(handle) != 0) {
        printf("FAIL: dlclose\n");
        failures |= 1;
    } else {
        printf("PASS: dlclose\n");
    }

    if (failures == 0)
        printf("RESULT: lcmaps-plugins-verify-proxy consumer checks passed\n");
    return failures != 0;
}
