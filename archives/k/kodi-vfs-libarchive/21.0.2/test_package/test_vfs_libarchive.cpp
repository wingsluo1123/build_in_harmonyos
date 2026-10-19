// Consumer-side verification for kodi-vfs-libarchive/21.0.2.
//
// A Kodi VFS add-on is a module loaded by the Kodi host; it has no standalone
// entry point and archive browsing is driven through host-provided callbacks
// (kodi::vfs Open/Read/Seek through CInstanceVFS), which do not exist without
// a Kodi host. What CAN be verified headlessly, against the packaged artifact
// itself, is:
//
//   [OHOS adaptation: explicit DT_NEEDED closure] The module is dlopen()ed on
//   the musl-based OHOS target. musl resolves every undefined symbol of the
//   loaded object at dlopen time (knowledge E004 BIND_NOW + the
//   lcmaps-plugins-basic experience entry: a dlopen-ed DSO's undefined
//   symbols resolve only against its own DT_NEEDED closure). The add-on calls
//   the libarchive public API directly, so a successful dlopen is only
//   possible when the recipe's explicit target_link_libraries(libarchive::archive)
//   produced a complete DT_NEEDED closure (libarchive.so, itself dynamically
//   depending on zstd).
//
//   [Kodi 21 binary add-on contract] the module exports the three C entry
//   points every Kodi 21 binary add-on defines through kodi/AddonBase.h
//   (ADDON_Create, ADDON_GetTypeVersion, ADDON_GetTypeMinVersion), and
//   ADDON_GetTypeVersion()/ADDON_GetTypeMinVersion() report the VFS instance
//   API version recorded in kodi/versions.h of the xbmc 21.3-Omega SDK:
//   ADDON_INSTANCE_VFS = 110, ADDON_INSTANCE_VERSION_VFS = "3.0.1"
//   (min "3.0.1"). This also validates the DRAFT-KODI01 macro policy: with
//   BUILD_KODI_ADDON/ADDON_*_USED not defined, versions.h compiles the full
//   version switch, so type 110 returns the real version string.
//
//   [dependency closure functional smoke] the test binary itself links the
//   Conan libarchive package the module depends on and exercises it
//   in-process (version macros + an archive_read instance create/free
//   roundtrip), proving the shared libarchive.so (+ its dynamic zstd
//   dependency) loads and runs on this target with the pinned 3.7.7 API.

#include <dlfcn.h>

#include <cstdio>
#include <cstring>

#include <archive.h>
#include <archive_entry.h>

int main(int argc, char** argv) {
    if (argc != 2) {
        std::fprintf(stderr, "usage: %s <path to vfs.libarchive.so>\n", argv[0]);
        return 2;
    }
    const char* module_path = argv[1];

    // ---- 1. The packaged module dlopen()s with a complete DT_NEEDED closure
    void* handle = dlopen(module_path, RTLD_LAZY | RTLD_LOCAL);
    if (handle == nullptr) {
        std::fprintf(stderr, "FAIL: dlopen(%s): %s\n", module_path, dlerror());
        return 1;
    }

    // ---- 2. Kodi binary add-on entry points
    const char* required_symbols[] = {
        "ADDON_Create",
        "ADDON_GetTypeVersion",
        "ADDON_GetTypeMinVersion",
    };
    for (const char* symbol : required_symbols) {
        void* entry = dlsym(handle, symbol);
        if (entry == nullptr) {
            std::fprintf(stderr, "FAIL: missing add-on entry point %s\n", symbol);
            dlclose(handle);
            return 1;
        }
    }

    using GetTypeVersionFn = const char* (*)(int);
    GetTypeVersionFn get_type_version = reinterpret_cast<GetTypeVersionFn>(
        dlsym(handle, "ADDON_GetTypeVersion"));
    GetTypeVersionFn get_type_min_version = reinterpret_cast<GetTypeVersionFn>(
        dlsym(handle, "ADDON_GetTypeMinVersion"));

    constexpr int kAddonInstanceVfs = 110;
    const char* version = get_type_version(kAddonInstanceVfs);
    if (version == nullptr || std::strcmp(version, "3.0.1") != 0) {
        std::fprintf(stderr, "FAIL: VFS instance version is %s, expected 3.0.1\n",
                     version == nullptr ? "<null>" : version);
        dlclose(handle);
        return 1;
    }
    const char* min_version = get_type_min_version(kAddonInstanceVfs);
    if (min_version == nullptr || std::strcmp(min_version, "3.0.1") != 0) {
        std::fprintf(stderr, "FAIL: VFS instance min version is %s, expected 3.0.1\n",
                     min_version == nullptr ? "<null>" : min_version);
        dlclose(handle);
        return 1;
    }

    dlclose(handle);

    // ---- 3. libarchive dependency closure is functional on this target
    const int libarchive_version = archive_version_number();
    if (libarchive_version != 3007007) {
        std::fprintf(stderr, "FAIL: libarchive version number is %d, expected 3007007 (3.7.7)\n",
                     libarchive_version);
        return 1;
    }
    const char* la_version_string = archive_version_string();
    if (la_version_string == nullptr ||
        std::strncmp(la_version_string, "libarchive", 10) != 0) {
        std::fprintf(stderr, "FAIL: libarchive version string is %s, expected a \"libarchive ...\" prefix\n",
                     la_version_string == nullptr ? "<null>" : la_version_string);
        return 1;
    }
    struct archive* reader = archive_read_new();
    if (reader == nullptr) {
        std::fprintf(stderr, "FAIL: archive_read_new() returned nullptr\n");
        return 1;
    }
    if (archive_read_free(reader) != ARCHIVE_OK) {
        std::fprintf(stderr, "FAIL: archive_read_free() did not return ARCHIVE_OK\n");
        return 1;
    }

    std::printf("PASS: %s exports the Kodi binary add-on entry points, reports "
                "VFS instance API 3.0.1, and its libarchive/3.7.7 dependency "
                "closure is functional\n",
                module_path);
    return 0;
}
