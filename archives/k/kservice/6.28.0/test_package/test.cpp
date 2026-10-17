// kservice 6.28.0 consumer test (R34: exercises the real API).
//
// Case A: constructs a temporary KService and verifies the desktop-service
//         accessors round-trip.
// Case B: end-to-end service discovery through the packaged library: a
//         desktop-file fixture is installed into the isolated XDG
//         applications directory, KSycoca::setupTestMenu() stages the
//         canonical minimal applications.menu (a sycoca build without a
//         menu has no application directories to scan), and KService
//         lookups drive the real KSycoca pipeline (cold cache -> in-process
//         cache build). The fixture must come back with its desktop entries
//         intact through both the desktop-name index
//         (serviceByDesktopName) and the entry-path index
//         (serviceByDesktopPath with the absolute entry path). A second
//         fixture staged by the conanfile under XDG_DATA_DIRS is looked up
//         the same way to cover the system data directory scan, and the
//         materialised sycoca cache file is verified.
#include <KService>
#include <KSycoca>
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QStandardPaths>
#include <QString>
#include <cstdio>

static int failures = 0;

static void check(bool condition, const char *message)
{
    if (condition) {
        std::printf("PASS: %s\n", message);
    } else {
        std::printf("FAIL: %s\n", message);
        ++failures;
    }
}

static bool writeFixture(const QString &path, const char *name, const char *exec, const char *icon)
{
    QDir().mkpath(QFileInfo(path).absolutePath());
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
        return false;
    }
    const QByteArray content = QByteArray("[Desktop Entry]\nType=Application\nName=") + name
        + "\nExec=" + exec + "\nIcon=" + icon + "\n";
    return file.write(content) == content.size();
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // ---- Case A: temporary KService object ----
    {
        KService service(QStringLiteral("OHOS Sample"),
                         QStringLiteral("sample-app --flag"),
                         QStringLiteral("sample-icon"));
        check(service.isApplication(), "case A: temporary service is an application");
        check(service.name() == QStringLiteral("OHOS Sample"), "case A: service name round-trips");
        check(service.exec() == QStringLiteral("sample-app --flag"), "case A: service exec round-trips");
        check(service.icon() == QStringLiteral("sample-icon"), "case A: service icon round-trips");
    }

    // ---- Case B: real discovery through the KSycoca pipeline ----
    {
        const QString writableApps =
            QStandardPaths::writableLocation(QStandardPaths::ApplicationsLocation);
        const QString writableFixture = writableApps + QStringLiteral("/org.kde.ohpc-sample.desktop");
        check(writeFixture(writableFixture, "OHPC Sample Service", "ohpc-sample --run", "ohpc-sample-icon"),
              "case B: fixture installed into the XDG applications directory");

        // Stage the library's canonical minimal applications.menu (with
        // DefaultAppDirs) into the isolated GenericConfigLocation; the
        // sycoca build finds its application directories through the menu.
        KSycoca::setupTestMenu();

        KSycoca::self()->ensureCacheValid();

        const KService::Ptr service =
            KService::serviceByDesktopName(QStringLiteral("org.kde.ohpc-sample"));
        check(service != nullptr, "case B: fixture discovered via serviceByDesktopName");
        if (service) {
            check(service->isApplication(), "case B: discovered service is an application");
            check(service->name() == QStringLiteral("OHPC Sample Service"),
                  "case B: discovered name matches the desktop entry");
            check(service->exec() == QStringLiteral("ohpc-sample --run"),
                  "case B: discovered exec matches the desktop entry");
            check(service->icon() == QStringLiteral("ohpc-sample-icon"),
                  "case B: discovered icon matches the desktop entry");
        }

        // Same entry through the entry-path index, keyed by the absolute
        // path of the desktop file.
        const KService::Ptr pathService = KService::serviceByDesktopPath(writableFixture);
        check(pathService != nullptr, "case B: fixture discovered via serviceByDesktopPath");

        const KService::Ptr envService =
            KService::serviceByDesktopName(QStringLiteral("org.kde.ohpc-envdirstest"));
        check(envService != nullptr && envService->name() == QStringLiteral("OHPC EnvDir Service"),
              "case B: XDG_DATA_DIRS fixture discovered");

        const QString cacheFile = KSycoca::absoluteFilePath();
        check(!cacheFile.isEmpty() && QFile::exists(cacheFile),
              "case B: sycoca cache file materialised");
        std::printf("INFO: sycoca cache at %s\n", qPrintable(cacheFile));
    }

    std::printf("TEST SUMMARY: %d failure(s)\n", failures);
    return failures == 0 ? 0 : 1;
}
