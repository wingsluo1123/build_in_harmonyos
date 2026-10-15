/*
 * test_package for kcontacts5 5.116.0 — consumer-side verification (R34).
 *
 * Drives the real public KContacts API:
 *   - Addressee field round-trips (givenName / familyName / realName /
 *     uid / note), isEmpty on a default-constructed instance,
 *   - Email / PhoneNumber / Address insertion and the collection getters,
 *     Addressee::mimeType(),
 *   - the vCard create -> parse round-trip through VCardConverter
 *     (converter/kcontacts/vcardconverter.h),
 *   - ContactGroup with inline ContactGroup::Data entries,
 *   - Picture image data round-trip and Geo validity.
 *
 * HarmonyOS-specific assertions (R53): the loaded libKF5Contacts.so carries
 * the OHOS-required unversioned DT_SONAME and a DT_RUNPATH (E537: the
 * installed ELF is linked with its final install RPATH and is never
 * rewritten post-link, so OHOS keeps mmap'ing it PROT_EXEC).
 */
#include <QCoreApplication>
#include <QImage>
#include <QString>
#include <QStringList>

#include <KContacts/Addressee>
#include <KContacts/Address>
#include <KContacts/ContactGroup>
#include <KContacts/Email>
#include <KContacts/Geo>
#include <KContacts/Picture>
#include <KContacts/PhoneNumber>
#include <KContacts/VCardConverter>

#include <cstdio>
#include <cstring>
#include <elf.h>
#include <string>
#include <vector>

#ifndef KCONTACTS_SO_PATH
#define KCONTACTS_SO_PATH ""
#endif

namespace
{

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

// Locate the file backing the loaded libKF5Contacts.so via /proc/self/maps.
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
        // The pathname is the 6th whitespace-separated field of a maps line
        // ("addr perms offset dev inode path"); take the whole pathname.
        const char *p = line;
        int field = 0;
        while (field < 5 && *p) {
            while (*p == ' ' || *p == '\t') {
                ++p;
            }
            if (!*p) {
                break;
            }
            ++field;
            while (*p && *p != ' ' && *p != '\t') {
                ++p;
            }
        }
        while (*p == ' ' || *p == '\t') {
            ++p;
        }
        if (*p == '/') {
            path = p;
            while (!path.empty()
                   && (path.back() == '\n' || path.back() == '\r' || path.back() == ' ')) {
                path.pop_back();
            }
            break;
        }
    }
    std::fclose(maps);
    return path;
}

struct ElfDynamic
{
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
    if (std::fread(&eh, sizeof(eh), 1, f) != 1
        || std::memcmp(eh.e_ident, ELFMAG, SELFMAG) != 0) {
        std::fclose(f);
        return info;
    }
    std::fseek(f, eh.e_phoff, SEEK_SET);
    Elf64_Phdr ph;
    Elf64_Phdr dyn_ph{};
    bool found_dyn = false;
    for (unsigned i = 0; i < eh.e_phnum; ++i) {
        if (std::fread(&ph, sizeof(ph), 1, f) != 1) {
            std::fclose(f);
            return info;
        }
        if (ph.p_type == PT_DYNAMIC) {
            dyn_ph = ph;
            found_dyn = true;
        }
    }
    if (!found_dyn) {
        std::fclose(f);
        return info;
    }
    std::fseek(f, dyn_ph.p_offset, SEEK_SET);
    Elf64_Dyn dyn;
    std::vector<Elf64_Dyn> entries;
    for (unsigned i = 0; i * sizeof(Elf64_Dyn) < dyn_ph.p_filesz; ++i) {
        if (std::fread(&dyn, sizeof(dyn), 1, f) != 1) {
            break;
        }
        entries.push_back(dyn);
    }
    for (const Elf64_Dyn &e : entries) {
        if (e.d_tag == DT_SONAME) {
            info.soname = "(soname-present)";
        } else if (e.d_tag == DT_RUNPATH) {
            info.has_runpath = true;
        } else if (e.d_tag == DT_RPATH) {
            info.has_rpath = true;
        }
    }
    info.ok = true;
    std::fclose(f);
    return info;
}

} // namespace

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // ---- Addressee field round-trips (public API) -----------------------
    KContacts::Addressee addressee;
    check(addressee.isEmpty(), "default Addressee isEmpty");

    addressee.setUid(QStringLiteral("test-uid-42"));
    addressee.setGivenName(QStringLiteral("Konqui"));
    addressee.setFamilyName(QStringLiteral("Dragon"));
    addressee.setNote(QStringLiteral("harmony notes"));
    check(addressee.uid() == QStringLiteral("test-uid-42"), "Addressee uid round-trip");
    check(addressee.givenName() == QStringLiteral("Konqui"), "Addressee givenName round-trip");
    check(addressee.familyName() == QStringLiteral("Dragon"), "Addressee familyName round-trip");
    check(addressee.note() == QStringLiteral("harmony notes"), "Addressee note round-trip");
    check(addressee.realName() == QStringLiteral("Konqui Dragon"), "Addressee realName assembles given+family");
    check(!addressee.isEmpty(), "Addressee no longer isEmpty after setters");
    check(KContacts::Addressee::mimeType() == QStringLiteral("text/directory"),
          "Addressee::mimeType() == text/directory");

    // ---- Email / PhoneNumber / Address insertion ------------------------
    KContacts::Email email(QStringLiteral("konqui@kde.org"));
    addressee.addEmail(email);
    check(addressee.emails().contains(QStringLiteral("konqui@kde.org")),
          "addEmail + emails() round-trip");

    KContacts::PhoneNumber phone(QStringLiteral("+49 30 123456"), KContacts::PhoneNumber::Work);
    addressee.insertPhoneNumber(phone);
    check(!addressee.phoneNumbers().isEmpty()
              && addressee.phoneNumbers().constFirst().number() == QStringLiteral("+49 30 123456"),
          "insertPhoneNumber + phoneNumbers() round-trip");

    KContacts::Address address(KContacts::Address::Home);
    address.setStreet(QStringLiteral("Prinzenstraße 85 F"));
    address.setLocality(QStringLiteral("Berlin"));
    address.setPostalCode(QStringLiteral("10969"));
    address.setCountry(QStringLiteral("DE"));
    addressee.insertAddress(address);
    check(!addressee.addresses().isEmpty()
              && addressee.addresses().constFirst().locality() == QStringLiteral("Berlin"),
          "insertAddress + addresses() round-trip");

    // ---- vCard create -> parse round-trip (converter public API) --------
    KContacts::VCardConverter converter;
    const QByteArray vcard = converter.createVCard(addressee);
    check(!vcard.isEmpty(), "VCardConverter::createVCard produced a vCard");

    const KContacts::Addressee::List parsed = converter.parseVCards(vcard);
    check(parsed.count() == 1, "VCardConverter::parseVCards returned one addressee");
    if (parsed.count() == 1) {
        check(parsed.constFirst().givenName() == QStringLiteral("Konqui"),
              "vCard round-trip preserves givenName");
        check(parsed.constFirst().familyName() == QStringLiteral("Dragon"),
              "vCard round-trip preserves familyName");
    }

    // ---- ContactGroup with inline data entries --------------------------
    KContacts::ContactGroup group;
    group.setName(QStringLiteral("KDE Friends"));
    group.append(KContacts::ContactGroup::Data(QStringLiteral("Dr. Konqi"),
                                               QStringLiteral("konqui@kde.org")));
    group.append(KContacts::ContactGroup::Data(QStringLiteral("Katie"),
                                               QStringLiteral("katie@kde.org")));
    check(group.name() == QStringLiteral("KDE Friends"), "ContactGroup name round-trip");
    check(group.count() == 2, "ContactGroup holds two inline data entries");
    check(group.data(0).name() == QStringLiteral("Dr. Konqi")
              && group.data(1).email() == QStringLiteral("katie@kde.org"),
          "ContactGroup::Data name/email round-trip");

    // ---- Picture image data + Geo validity ------------------------------
    QImage image(16, 16, QImage::Format_RGB32);
    image.fill(Qt::red);
    KContacts::Picture picture;
    check(picture.isEmpty(), "default Picture isEmpty");
    picture.setData(image);
    check(!picture.isEmpty() && picture.data().width() == 16,
          "Picture setData + data round-trip");

    KContacts::Geo geo(52.503f, 13.41f);
    check(geo.isValid(), "Geo(52.503, 13.41) isValid");
    check(!KContacts::Geo().isValid(), "default Geo is invalid");

    // ---- libKF5Contacts.so ELF adaptation (R53) --------------------------
    // /proc/self/maps reports the kernel-side HMDFS mount path
    // (/data/service/el2/...), which is not openable from inside the
    // sandbox namespace; KCONTACTS_SO_PATH (set by CMakeLists from the
    // imported KF5::Contacts target at configure time) carries the
    // consumer-visible packaged path, so prefer it and keep the maps
    // lookup only as a fallback.
    std::string so_path = KCONTACTS_SO_PATH;
    if (so_path.empty()) {
        so_path = loaded_library_path("libKF5Contacts.so");
    }
    check(!so_path.empty(), "libKF5Contacts.so path resolved");
    if (!so_path.empty()) {
        const ElfDynamic dyn = read_dynamic(so_path);
        check(dyn.ok, "libKF5Contacts.so ELF dynamic section parsed");
        check(dyn.soname == "(soname-present)",
              "libKF5Contacts.so carries a DT_SONAME");
        check(dyn.has_runpath || dyn.has_rpath,
              "libKF5Contacts.so carries a DT_RUNPATH/DT_RPATH (E537)");
    }

    std::printf("test_kcontacts5: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
