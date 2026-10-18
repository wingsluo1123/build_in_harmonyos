// OHOS-specific consumer executor for the kpeople HarmonyOS PC adaptation.
//
// The recipe aligns shared-library naming with the device filesystem: the
// HMDFS user volume rejects symlink() with EPERM, so
// CMAKE_PLATFORM_NO_VERSIONED_SONAME makes CMake emit a single unversioned
// libKF6People.so instead of the versioned symlink chain, while the recipe's
// explicit -soname linker flag (CMAKE_USER_MAKE_RULES_OVERRIDE defining
// CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG) still bakes a real DT_SONAME.
// Consumers therefore record a relocatable NEEDED name instead of the
// absolute conan-cache path of the build machine; musl performs no fallback
// lookup for slash-qualified NEEDED entries, so such binaries only run where
// the exact cache path exists.
//
// This executor parses its own ELF dynamic section and checks that the
// consumer linkage stayed SONAME-based: DT_NEEDED must contain exactly
// "libKF6People.so" and no slash-qualified absolute path.
//
// Every case prints its own "TEST PASS"/"TEST FAIL" line and the run ends
// with a TEST SUMMARY line; any failed case makes the process exit(1).
#include <KPeople/PersonData>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

#ifdef TP_REQUIRE_OHOS
#ifndef __OHOS__
#error "TP_REQUIRE_OHOS set but __OHOS__ is not defined: the OHOS toolchain triplet is not in effect"
#endif
#endif

namespace {

struct DynamicInfo {
    bool ok = false;
    std::string reason;
    std::vector<std::string> needed;
};

std::string selfPath(int argc, char **argv)
{
    std::ifstream probe("/proc/self/exe", std::ios::binary);
    if (probe.good()) {
        return "/proc/self/exe";
    }
    if (argc > 0 && argv[0]) {
        return argv[0];
    }
    return {};
}

bool vaddrToFileOffset(uint64_t addr,
                       const std::vector<char> &image,
                       uint64_t phoff,
                       uint16_t phnum,
                       uint64_t &fileOffset)
{
    for (uint16_t i = 0; i < phnum; ++i) {
        const uint64_t entry = phoff + static_cast<uint64_t>(i) * 56u;
        if (entry + 56u > image.size()) {
            return false;
        }
        uint32_t pType = 0;
        std::memcpy(&pType, image.data() + entry + 0, sizeof(pType));
        if (pType != 1u) { // PT_LOAD
            continue;
        }
        uint64_t pVaddr = 0;
        uint64_t pFilesz = 0;
        uint64_t pOffset = 0;
        std::memcpy(&pOffset, image.data() + entry + 8, sizeof(pOffset));
        std::memcpy(&pVaddr, image.data() + entry + 16, sizeof(pVaddr));
        std::memcpy(&pFilesz, image.data() + entry + 32, sizeof(pFilesz));
        if (addr >= pVaddr && addr - pVaddr < pFilesz) {
            fileOffset = addr - pVaddr + pOffset;
            return true;
        }
    }
    return false;
}

DynamicInfo readSelfDynamic(int argc, char **argv)
{
    DynamicInfo info;
    const std::string path = selfPath(argc, argv);
    if (path.empty()) {
        info.reason = "cannot determine self executable path";
        return info;
    }

    std::ifstream input(path, std::ios::binary);
    if (!input) {
        info.reason = "cannot open " + path;
        return info;
    }
    const std::vector<char> image((std::istreambuf_iterator<char>(input)),
                                  std::istreambuf_iterator<char>());
    if (image.size() < 64 || std::memcmp(image.data(), "\x7f" "ELF", 4) != 0) {
        info.reason = path + " is not an ELF image";
        return info;
    }
    const unsigned char eiClass = static_cast<unsigned char>(image[4]);
    const unsigned char eiData = static_cast<unsigned char>(image[5]);
    if (eiClass != 2u || eiData != 1u) {
        info.reason = "expected ELF64 little-endian image";
        return info;
    }

    uint64_t phoff = 0;
    uint16_t phentsize = 0;
    uint16_t phnum = 0;
    std::memcpy(&phoff, image.data() + 32, sizeof(phoff));
    std::memcpy(&phentsize, image.data() + 54, sizeof(phentsize));
    std::memcpy(&phnum, image.data() + 56, sizeof(phnum));
    if (phentsize != 56u) {
        info.reason = "unexpected program header entry size";
        return info;
    }

    uint64_t dynamicOffset = 0;
    uint64_t dynamicSize = 0;
    for (uint16_t i = 0; i < phnum; ++i) {
        const uint64_t entry = phoff + static_cast<uint64_t>(i) * phentsize;
        if (entry + 56u > image.size()) {
            info.reason = "program header table truncated";
            return info;
        }
        uint32_t pType = 0;
        std::memcpy(&pType, image.data() + entry + 0, sizeof(pType));
        if (pType != 2u) { // PT_DYNAMIC
            continue;
        }
        std::memcpy(&dynamicOffset, image.data() + entry + 8, sizeof(dynamicOffset));
        std::memcpy(&dynamicSize, image.data() + entry + 32, sizeof(dynamicSize));
    }
    if (dynamicOffset == 0 || dynamicSize == 0) {
        info.reason = "no PT_DYNAMIC segment found";
        return info;
    }

    uint64_t strtabAddr = 0;
    bool strtabFound = false;
    std::vector<uint64_t> neededOffsets;
    for (uint64_t pos = 0; pos + 16u <= dynamicSize; pos += 16u) {
        int64_t tag = 0;
        uint64_t value = 0;
        std::memcpy(&tag, image.data() + dynamicOffset + pos, sizeof(tag));
        std::memcpy(&value, image.data() + dynamicOffset + pos + 8, sizeof(value));
        if (tag == 0) { // DT_NULL
            break;
        }
        if (tag == 5) { // DT_STRTAB
            strtabAddr = value;
            strtabFound = true;
        } else if (tag == 1) { // DT_NEEDED
            neededOffsets.push_back(value);
        }
    }
    if (!strtabFound) {
        info.reason = "DT_STRTAB not found in dynamic section";
        return info;
    }
    uint64_t strtabFileOffset = 0;
    if (!vaddrToFileOffset(strtabAddr, image, phoff, phnum, strtabFileOffset)) {
        info.reason = "cannot map DT_STRTAB address to a file offset";
        return info;
    }

    for (uint64_t offset : neededOffsets) {
        const uint64_t at = strtabFileOffset + offset;
        if (at >= image.size()) {
            info.reason = "unreadable DT_NEEDED entry";
            return info;
        }
        const char *begin = image.data() + at;
        const uint64_t limit = image.size() - at;
        const char *end = static_cast<const char *>(std::memchr(begin, '\0', limit));
        if (!end) {
            info.reason = "unreadable DT_NEEDED entry";
            return info;
        }
        info.needed.emplace_back(begin, end);
    }

    info.ok = true;
    return info;
}

} // namespace

int main(int argc, char **argv)
{
    int passed = 0;
    int failed = 0;
    auto report = [&](bool ok, const char *name, const std::string &detail) {
        if (ok) {
            ++passed;
            std::printf("TEST PASS: %s\n", name);
        } else {
            ++failed;
            std::printf("TEST FAIL: %s (%s)\n", name, detail.c_str());
        }
        std::fflush(stdout);
    };

    // Case 1: the executable's own ELF dynamic section is readable.
    const DynamicInfo info = readSelfDynamic(argc, argv);
    report(info.ok, "self_elf_dynamic_readable", info.reason);
    if (!info.ok) {
        std::printf("TEST SUMMARY: %d/%d passed\n", passed, passed + failed);
        return 1;
    }

    // Case 2: the consumer references KF6People through the library SONAME.
    bool sonameEntry = false;
    bool noSlashQualified = true;
    std::string slashQualified;
    for (const std::string &name : info.needed) {
        if (name == "libKF6People.so") {
            sonameEntry = true;
        }
        if (!name.empty() && name.front() == '/') {
            noSlashQualified = false;
            slashQualified = name;
        }
    }
    report(sonameEntry,
           "dt_needed_soname_entry",
           "libKF6People.so missing from " + std::to_string(info.needed.size())
               + " DT_NEEDED entries");
    report(noSlashQualified,
           "no_slash_qualified_needed",
           "absolute DT_NEEDED baked in: " + slashQualified);

    // Case 3: live API touch guarantees the linkage is retained at runtime
    // (and that the shared library loads and runs under musl).
    report(std::strcmp(KPeople::PersonData::staticMetaObject.className(),
                       "KPeople::PersonData") == 0,
           "api_metaobject_live",
           "KPeople::PersonData metaobject unavailable at runtime");

    std::printf("TEST SUMMARY: %d/%d passed\n", passed, passed + failed);
    return failed == 0 ? 0 : 1;
}
