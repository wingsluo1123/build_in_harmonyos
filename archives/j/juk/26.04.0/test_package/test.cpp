// L1 consumer test for juk 26.04.0.
//
// juk is an application package: no library or header is exported, so this
// target cannot link juk itself. It verifies instead that the dependency chain
// juk is built and linked against is consumable from a fresh CMake project, by
// driving a real KF6 config key/value round-trip (KF6::ConfigCore, the config
// layer juk uses for its own settings). The juk artefact itself (binary
// presence, DT_NEEDED on the KIO widget libraries, --version execution) is
// checked in test_package/conanfile.py::test().
#include <cstdio>

#include <KConfigGroup>
#include <KSharedConfig>
#include <QString>

int main()
{
    const QString groupName = QStringLiteral("juk-test-package");

    {
        KSharedConfig::Ptr config = KSharedConfig::openConfig(QStringLiteral("juk-testrc"));
        KConfigGroup group(config, groupName);
        group.writeEntry(QStringLiteral("verified"), true);
        group.sync();
    }

    {
        KSharedConfig::Ptr config = KSharedConfig::openConfig(QStringLiteral("juk-testrc"));
        KConfigGroup group(config, groupName);
        if (!group.readEntry(QStringLiteral("verified"), false)) {
            std::fprintf(stderr, "KF6Config round-trip failed\n");
            return 1;
        }
    }

    std::printf("juk dependency chain OK (KF6Config round-trip)\n");
    return 0;
}
