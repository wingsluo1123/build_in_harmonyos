// test_package/test.cpp — consumer test for krunner5 5.116.0 on HarmonyOS PC.
//
// R34: links KF5::Runner and actually drives the public API after the
//      pattern of the upstream autotests (autotests/fakerunner.h): an
//      AbstractRunner subclass constructed from a KPluginMetaData, a
//      full match() -> RunnerContext::addMatch() -> matches() round trip,
//      QueryMatch value semantics (isValid/copy/ordering by relevance),
//      RunnerSyntax construction and the RunnerContext::matchesChanged
//      signal.
// R53: asserts the HarmonyOS adaptation path:
//      1. the loaded libKF5Runner.so carries the OHOS-required unversioned
//         DT_SONAME `libKF5Runner.so` (CMAKE_PLATFORM_NO_VERSIONED_SONAME)
//         and a DT_RUNPATH (E537: CMAKE_BUILD_WITH_INSTALL_RPATH=ON, so the
//         installed ELF is not rewritten after linking and stays loadable);
//      2. the packaged ELF carries a .codesign section (re-signed with
//         binary-sign-tool after install, OHOS loader requirement).
#include <elf.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include <QCoreApplication>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonValue>
#include <QList>
#include <QString>
#include <QStringList>
#include <QtGlobal>

#include <KPluginMetaData>

#include <KRunner/AbstractRunner>
#include <KRunner/QueryMatch>
#include <KRunner/RunnerContext>
#include <KRunner/RunnerSyntax>

// Injected by CMake ($<TARGET_FILE:KF5::Runner>): the packaged .so path.
#ifndef KRUNNER_SO_PATH
#define KRUNNER_SO_PATH ""
#endif

using namespace Plasma;

namespace {

int g_pass = 0;
int g_fail = 0;

void check(bool ok, const char *what)
{
    if (ok) {
        ++g_pass;
        std::printf("ok - %s\n", what);
    } else {
        ++g_fail;
        std::printf("FAIL - %s\n", what);
    }
}

const QLatin1String kRunnerName("krunner5 Consumer Test Runner");
const QLatin1String kRunnerDescription("krunner5 test_package consumer runner");

// The upstream autotests' FakeRunner pattern (autotests/fakerunner.h): an
// AbstractRunner subclass taking the tag-team constructor this 5.116 build
// exposes (the pre-5.116 constructors are compiled out by
// EXCLUDE_DEPRECATED_BEFORE_AND_AT=5.91.0).  addSyntax()/syntaxes() are
// protected, so re-expose them for the consumer assertions.
class ConsumerTestRunner : public AbstractRunner
{
public:
    ConsumerTestRunner(QObject *parent, const KPluginMetaData &metadata, const QVariantList &args)
        : AbstractRunner(parent, metadata, args)
    {
    }

    void match(RunnerContext &context) override
    {
        if (context.query() != QLatin1String("foo")) {
            return;
        }
        QueryMatch firstMatch(this);
        firstMatch.setId(QStringLiteral("foo"));
        firstMatch.setText(QStringLiteral("foo"));
        firstMatch.setRelevance(0.1);
        firstMatch.setCategoryRelevance(QueryMatch::CategoryRelevance::Highest);
        context.addMatch(firstMatch);

        QueryMatch secondMatch(this);
        secondMatch.setId(QStringLiteral("bar"));
        secondMatch.setText(QStringLiteral("bar"));
        secondMatch.setRelevance(0.2);
        secondMatch.setCategoryRelevance(QueryMatch::CategoryRelevance::Highest);
        context.addMatch(secondMatch);
    }

    using AbstractRunner::addSyntax;
    using AbstractRunner::syntaxes;
};

KPluginMetaData buildConsumerMetadata()
{
    // Same JSON shape as the KPlugin metadata files the runner plugins ship
    // ({"KPlugin": {...}}), parsed through the public KF5 API.
    const QByteArray json =
        R"({"KPlugin":{"Id":"testrunner","Name":"krunner5 Consumer Test Runner","Description":"krunner5 test_package consumer runner","Version":"1.0"}})";
    const QJsonObject root = QJsonDocument::fromJson(json).object();
    return KPluginMetaData(root, QStringLiteral("testrunner.json"));
}

// Locate the file backing the loaded libKF5Runner.so via /proc/self/maps.
std::string loaded_library_path(const char *needle)
{
    FILE *maps = std::fopen("/proc/self/maps", "r");
    if (!maps) {
        return std::string();
    }
    char line[8192];
    std::string path;
    while (std::fgets(line, sizeof(line), maps)) {
        if (!std::strstr(line, needle)) {
            continue;
        }
        const char *slash = std::strrchr(line, '/');
        if (slash) {
            path = slash;
            while (!path.empty() && (path.back() == '\n' || path.back() == '\r' || path.back() == ' ')) {
                path.pop_back();
            }
            break;
        }
    }
    std::fclose(maps);
    return path;
}

struct ElfDynamic {
    bool ok = false;
    std::string soname;
    bool has_runpath = false;
    bool has_rpath = false;
};

ElfDynamic read_dynamic(const std::string &path)
{
    ElfDynamic info;
    FILE *f = std::fopen(path.c_str(), "rb");
    if (!f) {
        return info;
    }
    Elf64_Ehdr eh;
    if (std::fread(&eh, sizeof(eh), 1, f) != 1 || std::memcmp(eh.e_ident, ELFMAG, SELFMAG) != 0
        || eh.e_ident[EI_CLASS] != ELFCLASS64) {
        std::fclose(f);
        return info;
    }
    struct Load {
        Elf64_Addr vaddr;
        Elf64_Off offset;
        Elf64_Xword filesz;
    };
    std::vector<Load> loads;
    Elf64_Phdr dyn_ph;
    bool have_dyn = false;
    for (int i = 0; i < eh.e_phnum; ++i) {
        if (std::fseek(f, static_cast<long>(eh.e_phoff + static_cast<Elf64_Off>(i) * eh.e_phentsize), SEEK_SET) != 0) {
            std::fclose(f);
            return info;
        }
        Elf64_Phdr ph;
        if (std::fread(&ph, sizeof(ph), 1, f) != 1) {
            std::fclose(f);
            return info;
        }
        if (ph.p_type == PT_LOAD) {
            loads.push_back({ph.p_vaddr, ph.p_offset, ph.p_filesz});
        } else if (ph.p_type == PT_DYNAMIC) {
            dyn_ph = ph;
            have_dyn = true;
        }
    }
    if (!have_dyn) {
        std::fclose(f);
        return info;
    }
    if (dyn_ph.p_filesz == 0 || dyn_ph.p_filesz % sizeof(Elf64_Dyn) != 0) {
        std::fclose(f);
        return info;
    }
    std::vector<Elf64_Dyn> dyn(dyn_ph.p_filesz / sizeof(Elf64_Dyn));
    if (std::fseek(f, static_cast<long>(dyn_ph.p_offset), SEEK_SET) != 0
        || std::fread(dyn.data(), sizeof(Elf64_Dyn), dyn.size(), f) != dyn.size()) {
        std::fclose(f);
        return info;
    }
    std::fclose(f);
    info.ok = true;
    for (const Elf64_Dyn &entry : dyn) {
        if (entry.d_tag == DT_NULL) {
            break;
        }
        if (entry.d_tag == DT_RUNPATH) {
            info.has_runpath = true;
        } else if (entry.d_tag == DT_RPATH) {
            info.has_rpath = true;
        }
    }
    return info;
}

// Resolve DT_SONAME through the dynamic string table (readelf-style).
std::string read_soname(const std::string &path)
{
    FILE *f = std::fopen(path.c_str(), "rb");
    if (!f) {
        return std::string();
    }
    Elf64_Ehdr eh;
    if (std::fread(&eh, sizeof(eh), 1, f) != 1 || std::memcmp(eh.e_ident, ELFMAG, SELFMAG) != 0) {
        std::fclose(f);
        return std::string();
    }
    struct Load {
        Elf64_Addr vaddr;
        Elf64_Off offset;
        Elf64_Xword filesz;
    };
    std::vector<Load> loads;
    Elf64_Phdr dyn_ph;
    bool have_dyn = false;
    for (int i = 0; i < eh.e_phnum; ++i) {
        if (std::fseek(f, static_cast<long>(eh.e_phoff + static_cast<Elf64_Off>(i) * eh.e_phentsize), SEEK_SET) != 0) {
            std::fclose(f);
            return std::string();
        }
        Elf64_Phdr ph;
        if (std::fread(&ph, sizeof(ph), 1, f) != 1) {
            std::fclose(f);
            return std::string();
        }
        if (ph.p_type == PT_LOAD) {
            loads.push_back({ph.p_vaddr, ph.p_offset, ph.p_filesz});
        } else if (ph.p_type == PT_DYNAMIC) {
            dyn_ph = ph;
            have_dyn = true;
        }
    }
    if (!have_dyn) {
        std::fclose(f);
        return std::string();
    }
    auto vaddr_to_off = [&loads](Elf64_Addr v) -> Elf64_Off {
        for (const Load &s : loads) {
            if (v >= s.vaddr && v < s.vaddr + s.filesz) {
                return s.offset + (v - s.vaddr);
            }
        }
        return 0;
    };
    std::vector<Elf64_Dyn> dyn(dyn_ph.p_filesz / sizeof(Elf64_Dyn));
    if (std::fseek(f, static_cast<long>(dyn_ph.p_offset), SEEK_SET) != 0
        || std::fread(dyn.data(), sizeof(Elf64_Dyn), dyn.size(), f) != dyn.size()) {
        std::fclose(f);
        return std::string();
    }
    std::string soname;
    for (const Elf64_Dyn &entry : dyn) {
        if (entry.d_tag == DT_NULL) {
            break;
        }
        if (entry.d_tag == DT_STRTAB) {
            Elf64_Off stroff = vaddr_to_off(entry.d_un.d_ptr);
            for (const Elf64_Dyn &strsz_entry : dyn) {
                if (strsz_entry.d_tag == DT_STRSZ) {
                    std::vector<char> strtab(strsz_entry.d_un.d_val);
                    if (stroff != 0
                        && (std::fseek(f, static_cast<long>(stroff), SEEK_SET) == 0)
                        && std::fread(strtab.data(), 1, strtab.size(), f) == strtab.size()) {
                        for (const Elf64_Dyn &soname_entry : dyn) {
                            if (soname_entry.d_tag == DT_SONAME
                                && soname_entry.d_un.d_val < strtab.size()) {
                                soname = std::string(strtab.data() + soname_entry.d_un.d_val);
                                break;
                            }
                        }
                    }
                    break;
                }
            }
            break;
        }
    }
    std::fclose(f);
    return soname;
}

// Check the packaged ELF carries a .codesign section (binary-sign-tool
// re-signing, OHOS loader requirement).
bool has_codesign_section(const std::string &path)
{
    FILE *f = std::fopen(path.c_str(), "rb");
    if (!f) {
        return false;
    }
    Elf64_Ehdr eh;
    if (std::fread(&eh, sizeof(eh), 1, f) != 1 || std::memcmp(eh.e_ident, ELFMAG, SELFMAG) != 0) {
        std::fclose(f);
        return false;
    }
    bool found = false;
    for (int i = 0; i < eh.e_shnum; ++i) {
        if (std::fseek(f, static_cast<long>(eh.e_shoff + static_cast<Elf64_Off>(i) * eh.e_shentsize), SEEK_SET) != 0) {
            break;
        }
        Elf64_Shdr sh;
        if (std::fread(&sh, sizeof(sh), 1, f) != 1) {
            break;
        }
        if (sh.sh_type == SHT_PROGBITS && sh.sh_name > 0) {
            std::vector<char> names;
            if (std::fseek(f, static_cast<long>(eh.e_shoff + static_cast<Elf64_Off>(eh.e_shstrndx) * eh.e_shentsize), SEEK_SET) == 0) {
                Elf64_Shdr names_sh;
                if (std::fread(&names_sh, sizeof(names_sh), 1, f) == 1 && names_sh.sh_type != SHT_NOBITS) {
                    names.resize(names_sh.sh_size);
                    if (std::fseek(f, static_cast<long>(names_sh.sh_offset), SEEK_SET) == 0
                        && std::fread(names.data(), 1, names.size(), f) == names.size()
                        && sh.sh_name < names.size()
                        && std::strcmp(names.data() + sh.sh_name, ".codesign") == 0) {
                        found = true;
                        break;
                    }
                }
            }
        }
    }
    std::fclose(f);
    return found;
}

} // namespace

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    std::setvbuf(stdout, nullptr, _IONBF, 0);

    // ── 1. KPluginMetaData plumbing (the runner's plugin metadata). ─────
    const KPluginMetaData metadata = buildConsumerMetadata();
    check(metadata.isValid(), "KPluginMetaData from the KPlugin JSON is valid");
    check(metadata.pluginId() == QLatin1String("testrunner"), "metadata pluginId round-trips");
    check(metadata.description() == kRunnerDescription, "metadata description round-trips");

    ConsumerTestRunner runner(nullptr, metadata, {});
    runner.setObjectName(QStringLiteral("testrunner"));
    check(runner.id() == QLatin1String("testrunner"), "runner.id() reports the plugin id");
    check(runner.description() == kRunnerDescription, "runner.description() reports the metadata description");

    // ── 2. match() -> RunnerContext::addMatch() -> matches(). ───────────
    RunnerContext context;
    context.setQuery(QStringLiteral("foo"));
    runner.match(context);
    const QList<QueryMatch> matches = context.matches();
    check(matches.size() == 2, "match() added the two QueryMatches to the RunnerContext");
    if (matches.size() == 2) {
        // QueryMatch::setId() composes the runner id with the given id
        // ("<runnerId>_<givenId>") unless the runner opts into unique results
        // (upstream querymatch.cpp), so the consumer-visible ids are prefixed.
        check(matches.at(0).id() == QLatin1String("testrunner_foo"), "first match id is composed with the runner id");
        check(matches.at(1).id() == QLatin1String("testrunner_bar"), "second match id is composed with the runner id");
        check(matches.at(0).text() == QLatin1String("foo"), "first match keeps its text");
        check(qFuzzyCompare(matches.at(0).relevance(), qreal(0.1)), "first match keeps its relevance");
        check(qFuzzyCompare(matches.at(1).relevance(), qreal(0.2)), "second match keeps its relevance");
        check(matches.at(0).isValid() && matches.at(1).isValid(), "added matches are valid (runner attached)");
        check(matches.at(0).runner() == &runner && matches.at(1).runner() == &runner, "matches point back at the runner");
    }

    RunnerContext otherContext;
    otherContext.setQuery(QStringLiteral("no-match-here"));
    runner.match(otherContext);
    check(otherContext.matches().isEmpty(), "a non-matching query yields no matches");

    // ── 3. QueryMatch value semantics. ──────────────────────────────────
    QueryMatch lowRelevance(&runner);
    lowRelevance.setId(QStringLiteral("low"));
    lowRelevance.setRelevance(0.1);
    QueryMatch highRelevance(&runner);
    highRelevance.setId(QStringLiteral("high"));
    highRelevance.setRelevance(0.2);
    check(lowRelevance < highRelevance, "operator< orders by relevance (lower relevance first)");
    check(!(highRelevance < lowRelevance), "operator< is asymmetric");
    const QueryMatch copy(lowRelevance);
    check(copy == lowRelevance, "copy shares the value (operator==)");
    check(copy != highRelevance, "different matches compare unequal");
    const QueryMatch empty;
    check(!empty.isValid(), "a default-constructed QueryMatch is not valid");

    // ── 4. RunnerContext::addMatches() bulk + matchesChanged. ───────────
    int changesCount = 0;
    QObject::connect(&otherContext, &RunnerContext::matchesChanged, [&changesCount]() {
        ++changesCount;
    });
    otherContext.setQuery(QStringLiteral("bulk"));
    check(otherContext.addMatches({lowRelevance, highRelevance}), "addMatches() accepts a bulk list");
    check(otherContext.matches().size() == 2, "bulk add added both matches");
    check(changesCount >= 1, "RunnerContext::matchesChanged was emitted");

    // ── 5. RunnerSyntax construction. ───────────────────────────────────
    RunnerSyntax syntax(QStringLiteral("krunner foo bar"), QStringLiteral("match the foo query"));
    runner.addSyntax(syntax);
    check(runner.syntaxes().size() >= 1, "addSyntax() registers a runner syntax");
    check(syntax.exampleQueries() == QStringList{QStringLiteral("krunner foo bar")},
          "RunnerSyntax keeps a plain example query verbatim");
    check(syntax.description() == QLatin1String("match the foo query"), "RunnerSyntax keeps its description");
    // Upstream rewrites the ":q:" placeholder into the localized term
    // description ("<search term>") when example queries are stored
    // (runnersyntax.cpp addExampleQuery), so ":q:" never survives.
    RunnerSyntax termSyntax(QStringLiteral(":q: foo"), QStringLiteral("search foo"));
    check(termSyntax.exampleQueries().size() == 1
              && !termSyntax.exampleQueries().first().contains(QLatin1String(":q:"))
              && termSyntax.exampleQueries().first().endsWith(QLatin1String(" foo")),
          "RunnerSyntax substitutes the :q: placeholder in example queries");
    RunnerSyntax multiSyntax(QStringList{QStringLiteral(":q: a"), QStringLiteral(":q: b")}, QStringLiteral("two forms"));
    check(multiSyntax.exampleQueries().size() == 2, "RunnerSyntax accepts several example queries");

    // ── R53 (1): OHOS ELF adaptation of the packaged library. ───────────
    std::string libPath = KRUNNER_SO_PATH;
    if (libPath.empty() || std::fopen(libPath.c_str(), "rb") == nullptr) {
        libPath = loaded_library_path("libKF5Runner.so");
    }
    check(!libPath.empty(), "HarmonyOS: libKF5Runner.so is mapped into the process");
    const ElfDynamic dyn = read_dynamic(libPath);
    const std::string soname = read_soname(libPath);
    std::printf("info - libKF5Runner.so = %s\n", libPath.c_str());
    std::printf("info - DT_SONAME = %s (RUNPATH=%d RPATH=%d)\n",
                soname.c_str(), int(dyn.has_runpath), int(dyn.has_rpath));
    check(dyn.ok && soname == "libKF5Runner.so",
          "HarmonyOS: libKF5Runner.so carries the unversioned DT_SONAME");
    check(dyn.ok && dyn.has_runpath,
          "HarmonyOS: libKF5Runner.so carries a DT_RUNPATH (E537 install-RPATH link)");

    // ── R53 (2): packaged ELF re-signed with binary-sign-tool. ──────────
    check(has_codesign_section(libPath),
          "HarmonyOS: packaged libKF5Runner.so carries a .codesign section (binary-sign-tool)");

    std::printf("SUMMARY: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
