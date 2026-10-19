// knewstuff5 test_package — R34: a real consumer must call the tested
// package's exported API and link its real symbols.
//
// The widgets layer (KNS3::Entry) is not part of the scoped OHOS package;
// this consumer therefore exercises genuine KNSCore classes that the
// packaged libKF5NewStuffCore exports:
//   - KNSCore::EntryInternal : data container (string/QUrl property round-trip)
//   - KNSCore::Author        : author record round-trip
//   - KNSCore::Engine        : real QObject-derived engine construction
// CamelCase headers installed under KNewStuff3/KNSCore.
#include <KNSCore/Author>
#include <KNSCore/Engine>
#include <KNSCore/EntryInternal>

#include <QUrl>

#include <cstdio>

using namespace KNSCore;

static int fail(const char *what)
{
    std::fprintf(stderr, "FAIL: %s\n", what);
    return 1;
}

int main(int argc, char **argv)
{
    (void)argc;
    (void)argv;

    // --- EntryInternal: real exported setters/getters round-trip ---
    EntryInternal entry;
    entry.setName(QStringLiteral("test-entry"));
    entry.setVersion(QStringLiteral("1.0"));
    entry.setCategory(QStringLiteral("wallpaper"));
    entry.setSummary(QStringLiteral("conan test_package entry"));
    entry.setHomepage(QUrl(QStringLiteral("https://example.org/entry")));

    if (entry.name() != QStringLiteral("test-entry")) {
        return fail("EntryInternal name round-trip broken");
    }
    if (entry.version() != QStringLiteral("1.0")) {
        return fail("EntryInternal version round-trip broken");
    }
    if (entry.category() != QStringLiteral("wallpaper")) {
        return fail("EntryInternal category round-trip broken");
    }
    if (entry.summary() != QStringLiteral("conan test_package entry")) {
        return fail("EntryInternal summary round-trip broken");
    }
    if (entry.homepage() != QUrl(QStringLiteral("https://example.org/entry"))) {
        return fail("EntryInternal homepage round-trip broken");
    }

    // --- Author: real exported author record round-trip ---
    Author author;
    author.setName(QStringLiteral("ohos-tester"));
    author.setEmail(QStringLiteral("tester@example.org"));
    if (author.name() != QStringLiteral("ohos-tester")) {
        return fail("Author name round-trip broken");
    }
    if (author.email() != QStringLiteral("tester@example.org")) {
        return fail("Author email round-trip broken");
    }
    entry.setAuthor(author);
    if (entry.author().name() != QStringLiteral("ohos-tester")) {
        return fail("EntryInternal author association broken");
    }

    // --- Engine: construct the real exported QObject engine ---
    Engine engine;
    if (engine.metaObject() == nullptr || engine.metaObject()->className() == nullptr) {
        return fail("Engine meta object unavailable");
    }

    std::printf("PASS: KNSCore EntryInternal/Author/Engine API round-trip OK\n");
    return 0;
}
