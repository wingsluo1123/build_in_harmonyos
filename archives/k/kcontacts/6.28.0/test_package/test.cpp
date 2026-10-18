// Consumer smoke test for the kcontacts/6.28.0 HarmonyOS PC package.
// Exercises the public API of the shipped libKF6Contacts.so: the
// Addressee/Address data models and the VCardConverter 3.0/4.0
// serialization round-trip (R34: real API usage, no stubs).
#include <KContacts/Addressee>
#include <KContacts/Address>
#include <KContacts/PhoneNumber>
#include <KContacts/VCardConverter>
// The version header installs directly at the exported include root
// (include/KF6/KContacts/kcontacts_version.h, see the INSTALL_INTERFACE of
// the KF6Contacts target), one level above the CamelCase KContacts/
// directory.
#include <kcontacts_version.h>

#include <QString>
#include <QStringList>

#include <cstdio>

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

int main()
{
    // 1) Version binding: the packaged headers report the 6.28.0 version.
    report("version header reports 6.28.0",
           QString::fromLatin1(KCONTACTS_VERSION_STRING) == QStringLiteral("6.28.0"));

    // 2) Addressee property model.
    KContacts::Addressee ada;
    ada.setName(QStringLiteral("Ada Lovelace"));
    // FN is its own vCard property (and the only name property vCard 4.0
    // requires), so set it explicitly together with the N components.
    ada.setFormattedName(QStringLiteral("Ada Lovelace"));
    ada.setFamilyName(QStringLiteral("Lovelace"));
    ada.setGivenName(QStringLiteral("Ada"));
    ada.setOrganization(QStringLiteral("KDE e.V."));
    ada.setEmails({QStringLiteral("ada@example.test")});
    KContacts::PhoneNumber number(QStringLiteral("+44 20 7946 0958"));
    ada.setPhoneNumbers({number});
    report("Addressee name/org/email/phone round-trip",
           ada.name() == QStringLiteral("Ada Lovelace")
               && ada.organization() == QStringLiteral("KDE e.V.")
               && ada.preferredEmail() == QStringLiteral("ada@example.test")
               && ada.phoneNumbers().size() == 1);

    // 3) Address sub-model.
    KContacts::Address address;
    address.setLocality(QStringLiteral("London"));
    address.setCountry(QStringLiteral("United Kingdom"));
    address.setPostalCode(QStringLiteral("SW1A 1AA"));
    ada.insertAddress(address);
    report("Address model round-trip",
           ada.addresses().size() == 1
               && ada.addresses().first().locality() == QStringLiteral("London")
               && ada.addresses().first().postalCode() == QStringLiteral("SW1A 1AA"));

    // 4) vCard 3.0 serialization (serializer lives in the packaged lib).
    KContacts::VCardConverter converter;
    const QByteArray vcard3 = converter.createVCard(ada, KContacts::VCardConverter::v3_0);
    report("vCard 3.0 serialize gives BEGIN/FN/EMAIL/TEL/ADR",
           vcard3.contains("BEGIN:VCARD")
               && vcard3.contains("FN:Ada Lovelace")
               && vcard3.contains("EMAIL:ada@example.test")
               && vcard3.contains("TEL")
               && vcard3.contains("ADR"),
           vcard3);

    // 5) vCard 3.0 parse round-trip.
    const KContacts::Addressee parsed3 = converter.parseVCard(vcard3);
    report("vCard 3.0 parse recovers name/email/address",
           parsed3.name() == QStringLiteral("Ada Lovelace")
               && parsed3.preferredEmail() == QStringLiteral("ada@example.test")
               && parsed3.addresses().size() == 1
               && parsed3.addresses().first().postalCode() == QStringLiteral("SW1A 1AA"));

    // 6) vCard 4.0 round-trip. vCard 4.0 has no NAME property (that only
    //    exists below 4.0), so the identity travels in FN plus the N
    //    components.
    const QByteArray vcard4 = converter.createVCard(ada, KContacts::VCardConverter::v4_0);
    const KContacts::Addressee parsed4 = converter.parseVCard(vcard4);
    report("vCard 4.0 round-trip recovers name/org",
           vcard4.contains("VERSION:4.0")
               && parsed4.formattedName() == QStringLiteral("Ada Lovelace")
               && parsed4.givenName() == QStringLiteral("Ada")
               && parsed4.familyName() == QStringLiteral("Lovelace")
               && parsed4.organization() == QStringLiteral("KDE e.V."),
           vcard4);

    // 7) Multi-contact list export/parse.
    KContacts::Addressee grace;
    grace.setName(QStringLiteral("Grace Hopper"));
    grace.setEmails({QStringLiteral("grace@example.test")});
    const KContacts::Addressee::List people{ada, grace};
    const KContacts::Addressee::List reparsed =
        converter.parseVCards(converter.createVCards(people, KContacts::VCardConverter::v3_0));
    report("multi-contact export/parse preserves both contacts",
           reparsed.size() == 2
               && reparsed.at(0).name() == QStringLiteral("Ada Lovelace")
               && reparsed.at(1).name() == QStringLiteral("Grace Hopper"));

    std::printf("TEST SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
