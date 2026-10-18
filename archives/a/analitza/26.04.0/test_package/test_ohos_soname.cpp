// OHOS SONAME/DT_NEEDED regression check for the analitza/26.04.0 package.
//
// The OHOS CMake toolchain emits no SONAME by default, so the recipe
// restores CMAKE_SHARED_LIBRARY_SONAME_* through
// CMAKE_USER_MAKE_RULES_OVERRIDE and sets
// CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE (E330: the HMDFS user volume
// cannot create the VERSION/SOVERSION symlink chain, so upstream's
// VERSION 9.0.0 lands as a single unversioned libAnalitzaPlot.so). That
// library must carry the bare DT_SONAME libAnalitzaPlot.so and must
// reference its dependencies by bare basenames only - no slash-qualified
// conan-cache or build-tree path may be recorded in DT_NEEDED (platform
// rule E537: the OHOS loader performs no fallback lookup for
// slash-qualified NEEDED entries, so such binaries only run where the
// exact build-tree path exists).
//
// This test parses the ELF dynamic section of both parties: its own (the
// consumer executable must stay SONAME-based) and the libAnalitzaPlot.so
// it has loaded (located through /proc/self/maps). The bare-SONAME contract
// is specific to the OHOS build: the recipe applies the unversioned-SONAME
// rules in its OHOS branch only, and test_package runs this check only there.
#include <analitza/analyzer.h>
#include <analitza/expression.h>
#include <analitzaplot/planecurve.h>
#include <analitzaplot/plotsfactory.h>

#include <QColor>
#include <QRectF>

#include <QByteArray>
#include <QString>

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

using namespace Analitza;

static int g_passed = 0;
static int g_failed = 0;

static void report(const char *name, bool ok, const QByteArray &debug = QByteArray())
{
    if (ok) {
        ++g_passed;
        std::printf("TEST PASS: %s\n", name);
    } else {
        ++g_failed;
        std::printf("TEST FAIL: %s\n", name);
        if (!debug.isEmpty()) {
            std::printf("--- debug artifact ---\n%s\n--- end debug artifact ---\n",
                        debug.constData());
        }
    }
}

namespace {

struct DynamicInfo {
    bool ok = false;
    std::string error;
    std::string soname;              // DT_SONAME, empty when absent
    std::vector<std::string> needed; // DT_NEEDED strings in dynamic order
    std::size_t slashEntries = 0;    // DT_NEEDED entries containing '/'
    bool bareAnalitzaPlotEntry = false; // a DT_NEEDED entry == "libAnalitzaPlot.so"
};

bool readImage(const std::string &path, std::vector<char> &image)
{
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        return false;
    }
    image.assign(std::istreambuf_iterator<char>(input),
                 std::istreambuf_iterator<char>());
    return !image.empty();
}

bool vaddrToFileOffset(uint64_t addr,
                       const std::vector<char> &image,
                       uint64_t phoff,
                       uint16_t phnum,
                       uint64_t &fileOffset)
{
    // Guard the whole program header table up front: entry = phoff + i * 56
    // can wrap around for a corrupt phoff, defeating the per-entry check.
    if (phoff > image.size()
        || static_cast<uint64_t>(phnum) > (image.size() - phoff) / 56u) {
        return false;
    }
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
            const uint64_t relative = addr - pVaddr;
            if (pOffset > image.size() || relative > image.size() - pOffset) {
                return false;
            }
            fileOffset = relative + pOffset;
            return true;
        }
    }
    return false;
}

DynamicInfo parseDynamic(const std::vector<char> &image)
{
    DynamicInfo info;
    if (image.size() < 64 || std::memcmp(image.data(), "\x7f" "ELF", 4) != 0) {
        info.error = "not an ELF image";
        return info;
    }
    const unsigned char eiClass = static_cast<unsigned char>(image[4]);
    const unsigned char eiData = static_cast<unsigned char>(image[5]);
    if (eiClass != 2u || eiData != 1u) {
        info.error = "expected an ELF64 little-endian image";
        return info;
    }

    uint64_t phoff = 0;
    uint16_t phentsize = 0;
    uint16_t phnum = 0;
    std::memcpy(&phoff, image.data() + 32, sizeof(phoff));
    std::memcpy(&phentsize, image.data() + 54, sizeof(phentsize));
    std::memcpy(&phnum, image.data() + 56, sizeof(phnum));
    if (phentsize != 56u) {
        info.error = "unexpected program header entry size";
        return info;
    }
    if (phoff > image.size()
        || static_cast<uint64_t>(phnum) > (image.size() - phoff) / phentsize) {
        info.error = "program header table out of bounds";
        return info;
    }

    uint64_t dynamicOffset = 0;
    uint64_t dynamicSize = 0;
    for (uint16_t i = 0; i < phnum; ++i) {
        const uint64_t entry = phoff + static_cast<uint64_t>(i) * phentsize;
        if (entry + 56u > image.size()) {
            info.error = "program header table truncated";
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
        info.error = "no PT_DYNAMIC segment found";
        return info;
    }
    if (dynamicOffset > image.size() || dynamicSize > image.size() - dynamicOffset) {
        info.error = "dynamic segment out of bounds";
        return info;
    }

    uint64_t strtabAddr = 0;
    bool strtabFound = false;
    uint64_t sonameOffset = 0;
    bool sonameFound = false;
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
        } else if (tag == 14) { // DT_SONAME
            sonameOffset = value;
            sonameFound = true;
        }
    }
    if (!strtabFound) {
        info.error = "DT_STRTAB not found in the dynamic section";
        return info;
    }
    uint64_t strtabFileOffset = 0;
    if (!vaddrToFileOffset(strtabAddr, image, phoff, phnum, strtabFileOffset)) {
        info.error = "cannot map the DT_STRTAB address to a file offset";
        return info;
    }

    auto stringAt = [&](uint64_t offset) -> std::string {
        const uint64_t at = strtabFileOffset + offset;
        if (at >= image.size()) {
            return {};
        }
        const char *begin = image.data() + at;
        const uint64_t limit = image.size() - at;
        const char *end = static_cast<const char *>(std::memchr(begin, '\0', limit));
        if (!end) {
            return {};
        }
        return std::string(begin, end);
    };

    if (sonameFound) {
        info.soname = stringAt(sonameOffset);
    }
    for (uint64_t offset : neededOffsets) {
        const std::string name = stringAt(offset);
        if (name.empty()) {
            info.error = "unreadable DT_NEEDED entry";
            return info;
        }
        if (name.find('/') != std::string::npos) {
            ++info.slashEntries;
        }
        // The consumer links the unversioned AnalitzaPlot library, so the
        // loader-visible name is the bare SONAME (E330).
        if (name == "libAnalitzaPlot.so") {
            info.bareAnalitzaPlotEntry = true;
        }
        info.needed.push_back(name);
    }
    info.ok = true;
    return info;
}

std::string loadedAnalitzaPlotPath()
{
    std::ifstream maps("/proc/self/maps");
    if (!maps) {
        return {};
    }
    std::string line;
    while (std::getline(maps, line)) {
        const std::string::size_type pos = line.find("/libAnalitzaPlot.so");
        if (pos == std::string::npos) {
            continue;
        }
        // Take the whole pathname: it is the last field of the maps line
        // ("address perms offset dev inode pathname"), so start at the
        // blank right before it (pathnames contain no blanks; the kernel
        // escapes any as \040).
        const std::string::size_type start = line.rfind(' ', pos);
        std::string path =
            start == std::string::npos ? line : line.substr(start + 1);
        while (!path.empty()
               && (path.back() == ' ' || path.back() == '\r' || path.back() == '\n')) {
            path.pop_back();
        }
        return path;
    }
    return {};
}

std::vector<std::string> analitzaPlotPathCandidates()
{
    std::vector<std::string> candidates;
    // Re-opening the library through the same LD_LIBRARY_PATH list the loader
    // used is the reliable way to reach the packaged file: the
    // /proc/self/maps pathname is the kernel-side canonical view of the
    // cache, which is not guaranteed to be openable from this process (HMDFS
    // mount views differ between namespaces). The unversioned name is the
    // shipped layout; the versioned fallback only matches a non-OHOS build.
    if (const char *ld = std::getenv("LD_LIBRARY_PATH")) {
        const std::string list(ld);
        std::string::size_type start = 0;
        for (;;) {
            const std::string::size_type end = list.find(':', start);
            const std::string dir = end == std::string::npos
                                        ? list.substr(start)
                                        : list.substr(start, end - start);
            if (!dir.empty()) {
                candidates.push_back(dir + "/libAnalitzaPlot.so");
                candidates.push_back(dir + "/libAnalitzaPlot.so.9");
            }
            if (end == std::string::npos) {
                break;
            }
            start = end + 1;
        }
    }
    const std::string mapped = loadedAnalitzaPlotPath();
    if (!mapped.empty()) {
        candidates.push_back(mapped);
    }
    return candidates;
}

QByteArray toQ(const std::string &value)
{
    return QByteArray(value.c_str(), static_cast<int>(value.size()));
}

QByteArray joined(const std::vector<std::string> &names)
{
    std::string out;
    for (const std::string &name : names) {
        out += name;
        out += '\n';
    }
    return toQ(out);
}

} // namespace

int main()
{
    // 1) Real API touch: guarantees the linkage is live (KF6::AnalitzaPlot
    //    is not dropped by --as-needed) and that the shared library loads.
    //    The factory path exercises Analitza + AnalitzaPlot together.
    const Expression expression(QStringLiteral("x^2"));
    const PlotBuilder builder =
        PlotsFactory::self()->requestPlot(expression, Analitza::Dim2D);
    report("AnalitzaPlot API touch works in the consumer process",
           builder.canDraw());

    // 2) + 3) The consumer executable itself: DT_NEEDED must stay
    //    SONAME-based, i.e. bare basenames only (no slash-qualified
    //    cache path baked in) and a reference to the bare
    //    libAnalitzaPlot.so SONAME.
    std::vector<char> selfImage;
    readImage("/proc/self/exe", selfImage);
    const DynamicInfo selfInfo = parseDynamic(selfImage);
    const QByteArray selfDebug =
        selfInfo.ok ? joined(selfInfo.needed) : toQ(selfInfo.error);
    report("consumer executable DT_NEEDED entries are all basenames",
           selfInfo.ok && selfInfo.slashEntries == 0,
           selfDebug);
    report("consumer executable references libAnalitzaPlot.so by bare SONAME",
           selfInfo.ok && selfInfo.bareAnalitzaPlotEntry,
           selfDebug);

    // 4) The produced library, re-opened through the candidate list the
    //    loader itself used (LD_LIBRARY_PATH, then the maps pathname as a
    //    fallback) and parsed from disk.
    std::string libPath;
    std::vector<char> libImage;
    std::string candidatesTried;
    for (const std::string &candidate : analitzaPlotPathCandidates()) {
        candidatesTried += candidate;
        candidatesTried += '\n';
        if (readImage(candidate, libImage)) {
            libPath = candidate;
            break;
        }
    }
    const DynamicInfo libInfo = parseDynamic(libImage);
    const QByteArray libDebug =
        libInfo.ok
            ? toQ(libPath)
            : toQ("opened: " + (libPath.empty() ? std::string("(none)") : libPath)
                  + "\nparse error: " + libInfo.error
                  + "\ntried:\n"
                  + (candidatesTried.empty() ? std::string("(no candidates)\n")
                                             : candidatesTried));
    report("loaded libAnalitzaPlot.so located and parsed",
           !libPath.empty() && libInfo.ok,
           libDebug);

    // 5) + 6) The library's own dynamic section: a bare DT_SONAME
    //    (libAnalitzaPlot.so under CMAKE_PLATFORM_NO_VERSIONED_SONAME) and
    //    bare basenames only in DT_NEEDED (E537 regression net).
    report("libAnalitzaPlot.so DT_SONAME is the bare basename",
           libInfo.ok && libInfo.soname == "libAnalitzaPlot.so",
           libInfo.ok ? toQ(libInfo.soname) : libDebug);
    report("libAnalitzaPlot.so DT_NEEDED entries are all basenames (E537)",
           libInfo.ok && libInfo.slashEntries == 0 && !libInfo.needed.empty(),
           libInfo.ok ? joined(libInfo.needed) : libDebug);

    std::printf("TEST SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
