// test_package consumer probe: dlopen the installed scim-thai IMEngine
// module and verify the SCIM factory symbol is exported and callable.
#include <dlfcn.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>

int main(int argc, char** argv) {
    if (argc < 2) {
        std::fprintf(stderr, "usage: test_probe <path-to-thai.so>\n");
        return 2;
    }
    const char* module = argv[1];
    void* handle = dlopen(module, RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        std::fprintf(stderr, "dlopen(%s) failed: %s\n", module, dlerror());
        return 1;
    }
    // SCIM loads IMEngine modules through scim_imengine_module_create_factory
    // (symbol macro-expanded with the module LTX prefix).
    const char* symbols[] = {
        "thai_LTX_scim_imengine_module_create_factory",
        "scim_imengine_module_create_factory",
        nullptr,
    };
    bool found = false;
    for (int i = 0; symbols[i]; ++i) {
        void* sym = dlsym(handle, symbols[i]);
        if (sym) {
            std::printf("scim-thai module OK: %s -> %p\n", symbols[i], sym);
            found = true;
            break;
        }
    }
    dlclose(handle);
    if (!found) {
        std::fprintf(stderr,
                     "scim_imengine_module_create_factory not found in %s\n",
                     module);
        return 1;
    }
    return 0;
}
