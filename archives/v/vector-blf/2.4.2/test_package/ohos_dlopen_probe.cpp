// test_package/ohos_dlopen_probe.cpp
//
// HarmonyOS ELF loadability probe.
//
// This executable deliberately does NOT link vector-blf and does not include any
// of its headers: the OHOS loader therefore maps the packaged libVector_BLF.so
// for the first time inside this process, which is what makes the check
// meaningful (an in-process dlopen from a binary that already links the library
// would be implied by the dynamic linker before main()).
//
// 用法: ohos_dlopen_probe <path-to-libVector_BLF.so>

#include <dlfcn.h>

#include <cstdio>

namespace {

const char * kSymbols[] = {
    "_ZN6Vector3BLF4File4readEv",         // File::read()
    "_ZN6Vector3BLF10CanMessageC1Ev",     // CanMessage::CanMessage()
    "_ZTVN6Vector3BLF10CanMessageE",      // vtable for CanMessage
};

}  // namespace

int main(int argc, char * argv[]) {
    if (argc < 2) {
        std::fprintf(stderr, "usage: ohos_dlopen_probe <libVector_BLF.so>\n");
        return 2;
    }
    void * handle = ::dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (handle == nullptr) {
        std::fprintf(stderr, "ohos_dlopen_probe: dlopen failed: %s\n", ::dlerror());
        return 1;
    }
    const char * found = nullptr;
    for (const char * symbol : kSymbols) {
        if (::dlsym(handle, symbol) != nullptr) {
            found = symbol;
            break;
        }
    }
    if (found == nullptr) {
        std::fprintf(stderr, "ohos_dlopen_probe: no expected exported symbol found\n");
        ::dlclose(handle);
        return 1;
    }
    std::printf("ohos dlopen probe: loaded %s, symbol=%s\n", argv[1], found);
    ::dlclose(handle);
    return 0;
}
