// test_package/test.cpp — consumer test for kdb 3.2.0 on HarmonyOS PC.
//
// R34: links the exported `KDb` target and drives the real public API end to
//      end after the pattern of the upstream autotests
//      (autotests/KDbTestUtils.cpp + tests/features/tables_test_p.h):
//      KDbDriverManager discovery of the installed org.kde.kdb.sqlite driver
//      plugin, KDbDriverMetaData inspection, the full KDbConnection lifecycle
//      (connect/createDatabase/databaseExists/useDatabase/
//      databaseProperties), KDbTableSchema/KDbField DDL, insertRecord,
//      querySingleString/querySingleNumber reads (including the error path),
//      the explicit transaction API (setAutoCommit(false) +
//      beginTransaction() + commitTransaction()) and the idempotent
//      close/disconnect/dropDatabase teardown.
// R53: asserts the HarmonyOS adaptation path:
//      1. the loaded libKDb3.so carries the OHOS-required unversioned
//         DT_SONAME `libKDb3.so` (CMAKE_PLATFORM_NO_VERSIONED_SONAME) and a
//         DT_RUNPATH (E537: CMAKE_BUILD_WITH_INSTALL_RPATH=ON, so the
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
#include <QString>
#include <QStringList>
#include <QTemporaryDir>
#include <QVariant>
#include <QtGlobal>

#include <KDb>
#include <KDbConnection>
#include <KDbConnectionData>
#include <KDbDriver>
#include <KDbDriverManager>
#include <KDbDriverMetaData>
#include <KDbEscapedString>
#include <KDbField>
#include <KDbProperties>
#include <KDbSqlResult>
#include <KDbTableSchema>
#include <KDbTransaction>
#include <KDbVersionInfo>

// Injected by CMake ($<TARGET_FILE:KDb>): the packaged libKDb3.so path.
#ifndef KDB_SO_PATH
#define KDB_SO_PATH ""
#endif

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

// Locate the file backing the loaded libKDb3.so via /proc/self/maps.
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

    // ── 1. Library version (KDb::version(), KDbVersionInfo). ────────────
    const KDbVersionInfo version = KDb::version();
    std::printf("info - KDb::version() = %d.%d.%d\n",
                version.major(), version.minor(), version.release());
    check(version.major() == 3 && version.minor() == 2, "KDb::version() reports the 3.2 series");
    const KDbVersionInfo manual(9, 8, 7);
    check(manual.major() == 9 && manual.minor() == 8 && manual.release() == 7,
          "KDbVersionInfo round-trips its major/minor/release components");

    // ── 2. Driver plugin discovery (org.kde.kdb.sqlite is installed). ───
    KDbDriverManager manager;
    const QStringList driverIds = manager.driverIds();
    check(driverIds.contains(QStringLiteral("org.kde.kdb.sqlite")),
          "KDbDriverManager::driverIds() lists org.kde.kdb.sqlite");
    const KDbDriverMetaData *const metaData = manager.driverMetaData(QStringLiteral("org.kde.kdb.sqlite"));
    check(metaData != nullptr, "driverMetaData() returns metadata for the sqlite driver");
    check(metaData && metaData->isFileBased(), "sqlite driver metadata reports a file-based driver");
    KDbDriver *const driver = manager.driver(QStringLiteral("org.kde.kdb.sqlite"));
    check(driver != nullptr, "driver() instantiates the sqlite driver plugin");

    // ── 3. Connection lifecycle (connect/create/use/properties). ────────
    QTemporaryDir tempDir;
    check(tempDir.isValid(), "QTemporaryDir for the test database is valid");
    const QString dbPath = tempDir.filePath(QStringLiteral("kdb_test.kexi"));
    std::printf("info - database path = %s\n", qPrintable(dbPath));

    KDbConnectionData cdata;
    cdata.setDriverId(QStringLiteral("org.kde.kdb.sqlite"));
    cdata.setDatabaseName(dbPath);
    KDbConnection *const conn = driver ? driver->createConnection(cdata) : nullptr;
    check(conn != nullptr, "createConnection() returns a connection handle");
    if (!conn) {
        std::printf("SUMMARY: %d passed, %d failed\n", g_pass, g_fail);
        return 1;
    }
    check(driver->connections().count() == 1, "the driver tracks the created connection");
    check(conn->connect(), "connect() succeeds");
    check(conn->isConnected(), "isConnected() is true after connect()");
    check(!conn->databaseExists(dbPath), "databaseExists() is false before createDatabase()");
    check(conn->createDatabase(dbPath), "createDatabase() succeeds");
    check(conn->databaseExists(dbPath), "databaseExists() is true after createDatabase()");
    check(conn->useDatabase(), "useDatabase() succeeds");
    check(conn->isDatabaseUsed(), "isDatabaseUsed() is true after useDatabase()");
    KDbProperties properties = conn->databaseProperties();
    check(properties.names().contains(QStringLiteral("kexidb_major_ver")),
          "databaseProperties() exposes the kexidb_major_ver entry");
    bool ok = false;
    const int storedMajor = properties.value(QStringLiteral("kexidb_major_ver")).toInt(&ok);
    check(ok && storedMajor == version.major(), "stored kexidb_major_ver matches KDb::version().major()");

    // ── 4. DDL + data inside an explicit transaction (upstream pattern,
    //       tests/features/tables_test_p.h). ────────────────────────────
    check(conn->setAutoCommit(false), "setAutoCommit(false) succeeds");
    KDbTransaction transaction = conn->beginTransaction();
    check(!conn->result().isError(), "beginTransaction() starts without error");
    KDbTableSchema *const persons = new KDbTableSchema(QStringLiteral("persons"));
    persons->setCaption(QStringLiteral("Persons in our factory"));
    KDbField *field = nullptr;
    persons->addField(field = new KDbField(QStringLiteral("id"), KDbField::Integer,
                                           KDbField::PrimaryKey | KDbField::AutoInc, KDbField::Unsigned));
    field->setCaption(QStringLiteral("ID"));
    persons->addField(field = new KDbField(QStringLiteral("age"), KDbField::Integer,
                                           KDbField::NoConstraints, KDbField::Unsigned));
    field->setCaption(QStringLiteral("Age"));
    persons->addField(field = new KDbField(QStringLiteral("name"), KDbField::Text));
    field->setCaption(QStringLiteral("Name"));
    persons->addField(field = new KDbField(QStringLiteral("surname"), KDbField::Text));
    field->setCaption(QStringLiteral("Surname"));
    check(conn->createTable(persons), "createTable() creates the persons table");
    check(conn->containsTable(QStringLiteral("persons")) == true, "containsTable() sees the new table");
    check(conn->tableNames().contains(QStringLiteral("persons")), "tableNames() lists the new table");
    const QSharedPointer<KDbSqlResult> insert1 = conn->insertRecord(persons, QVariant(1), QVariant(27),
                                                                    QVariant(QStringLiteral("Jaroslaw")),
                                                                    QVariant(QStringLiteral("Staniek")));
    check(!insert1.isNull(), "insertRecord() row 1 (Jaroslaw Staniek) succeeds");
    const QSharedPointer<KDbSqlResult> insert2 = conn->insertRecord(persons, QVariant(2), QVariant(60),
                                                                    QVariant(QStringLiteral("Lech")),
                                                                    QVariant(QStringLiteral("Walesa")));
    check(!insert2.isNull(), "insertRecord() row 2 (Lech Walesa) succeeds");
    check(conn->commitTransaction(transaction), "commitTransaction() succeeds");
    check(conn->setAutoCommit(true), "setAutoCommit(true) restores the default");

    // ── 5. Reads: querySingleString()/querySingleNumber() (+ error path).
    QString name;
    check(conn->querySingleString(KDbEscapedString(QStringLiteral("SELECT name FROM persons WHERE id = 1")),
                                  &name) == true,
          "querySingleString() succeeds for an existing row");
    check(name == QStringLiteral("Jaroslaw"), "querySingleString() returns the stored name");
    int count = -1;
    check(conn->querySingleNumber(KDbEscapedString(QStringLiteral("SELECT COUNT(*) FROM persons")),
                                  &count) == true,
          "querySingleNumber() succeeds for COUNT(*)");
    check(count == 2, "COUNT(*) sees both committed rows");
    QString missing;
    check(conn->querySingleString(KDbEscapedString(QStringLiteral("SELECT name FROM no_such_table_xyz")),
                                  &missing) != true,
          "querySingleString() on a missing table does not report success");

    // ── 6. Idempotent teardown + dropDatabase (upstream pattern). ───────
    check(conn->closeDatabase(), "closeDatabase() succeeds");
    check(!conn->isDatabaseUsed(), "isDatabaseUsed() is false after closeDatabase()");
    check(conn->closeDatabase(), "second closeDatabase() is a no-op success");
    check(conn->disconnect(), "disconnect() succeeds");
    check(!conn->isConnected(), "isConnected() is false after disconnect()");
    check(conn->disconnect(), "second disconnect() is a no-op success");
    check(conn->dropDatabase(dbPath), "dropDatabase() removes the database file");
    check(!conn->databaseExists(dbPath), "databaseExists() is false after dropDatabase()");
    delete conn;
    check(driver->connections().count() == 0, "the connection is unregistered from the driver after delete");

    // ── R53 (1): OHOS ELF adaptation of the packaged library. ───────────
    std::string libPath = KDB_SO_PATH;
    if (libPath.empty() || std::fopen(libPath.c_str(), "rb") == nullptr) {
        libPath = loaded_library_path("libKDb3.so");
    }
    check(!libPath.empty(), "HarmonyOS: libKDb3.so is mapped into the process");
    const ElfDynamic dyn = read_dynamic(libPath);
    const std::string soname = read_soname(libPath);
    std::printf("info - libKDb3.so = %s\n", libPath.c_str());
    std::printf("info - DT_SONAME = %s (RUNPATH=%d RPATH=%d)\n",
                soname.c_str(), int(dyn.has_runpath), int(dyn.has_rpath));
    check(dyn.ok && soname == "libKDb3.so",
          "HarmonyOS: libKDb3.so carries the unversioned DT_SONAME");
    check(dyn.ok && dyn.has_runpath,
          "HarmonyOS: libKDb3.so carries a DT_RUNPATH (E537 install-RPATH link)");

    // ── R53 (2): packaged ELF re-signed with binary-sign-tool. ──────────
    check(has_codesign_section(libPath),
          "HarmonyOS: packaged libKDb3.so carries a .codesign section (binary-sign-tool)");

    std::printf("SUMMARY: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
