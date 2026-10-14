// kservice5 5.116.0 consumer test (R34: exercises real API).
//
// Part 1 — link-and-behave on the installed package: the in-memory
// KService(name, exec, icon) constructor, the accessors, instance isolation
// and the copy constructor (the shape the KF6 kservice/6.18.0 test_package in
// this repository uses).
//
// Part 2 — HarmonyOS-specific end-to-end use case: OHOS has no XDG data dirs,
// no ksycoca database and no session-wide kbuildsycoca5 run.  A consumer must
// therefore be able to build its own XDG tree, generate the database with the
// kbuildsycoca5 that ships inside the package, and then look the service up
// again through KSycoca.  That is the platform-specific contract this package
// has to satisfy on OHOS, and it is checked here as a real round trip
// (populate -> index -> query), not as a bare assertion.
#include <KService>

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QProcess>
#include <QProcessEnvironment>
#include <QStandardPaths>
#include <QString>
#include <QTemporaryDir>

#include <cstdio>

static int failures = 0;
static int total = 0;

static void check(bool ok, const char *what)
{
    ++total;
    std::printf("%s: %s\n", ok ? "ok" : "FAIL", what);
    if (!ok) {
        ++failures;
    }
}

static bool writeFile(const QString &path, const QByteArray &contents)
{
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return false;
    }
    const bool ok = file.write(contents) == contents.size();
    file.close();
    return ok;
}

int main(int argc, char **argv)
{
    // The XDG locations must be in place before QStandardPaths (and therefore
    // KSycoca) is used for the first time.
    QTemporaryDir root;
    if (!root.isValid()) {
        std::printf("FAIL: could not create a temporary XDG tree\n");
        return 1;
    }
    const QString dataHome = root.path() + QStringLiteral("/data");
    const QString cacheHome = root.path() + QStringLiteral("/cache");
    const QString configHome = root.path() + QStringLiteral("/config");
    const QString home = root.path() + QStringLiteral("/home");
    for (const QString &dir : {dataHome, cacheHome, configHome, home}) {
        QDir().mkpath(dir);
    }
    qputenv("XDG_DATA_HOME", dataHome.toUtf8());
    qputenv("XDG_DATA_DIRS", dataHome.toUtf8());
    qputenv("XDG_CACHE_HOME", cacheHome.toUtf8());
    qputenv("XDG_CONFIG_HOME", configHome.toUtf8());
    qputenv("HOME", home.toUtf8());
    qputenv("QT_QPA_PLATFORM", "offscreen");

    QCoreApplication app(argc, argv);

    // ---- Part 2b: build the XDG tree and the database, then look it up -----
    // KSycoca is a per-process singleton, so the database has to exist before
    // anything triggers its first use: nothing above this point may query it.
    const QString appDir = dataHome + QStringLiteral("/applications");
    QDir().mkpath(appDir);
    const QString desktopFile = appDir + QStringLiteral("/ohos-consumer.desktop");
    check(writeFile(desktopFile,
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    "Name=OHOS Consumer Sample\n"
                    "Exec=sample-app --flag\n"
                    "Icon=sample-icon\n"),
          "the consumer can install a .desktop file into its own XDG data dir");

    const QString binDir = qEnvironmentVariable("KSERVICE5_BIN_DIR");

    // The freedesktop menu definition a bare OHOS image does not have: the
    // package installs one (etc/xdg/menus/applications.menu) and, exactly like
    // a desktop session, the consumer stages it into its own XDG config tree
    // before the database is built.
    const QString menusDir = configHome + QStringLiteral("/menus");
    QDir().mkpath(menusDir);
    const QString pkgMenu =
        QDir(binDir).absoluteFilePath(QStringLiteral("../etc/xdg/menus/applications.menu"));
    check(QFile::exists(pkgMenu) &&
              QFile::copy(pkgMenu, menusDir + QStringLiteral("/applications.menu")),
          "the consumer stages the applications.menu shipped inside the package");


    if (binDir.isEmpty()) {
        check(false, "KSERVICE5_BIN_DIR is set by the test driver (package bin dir)");
    } else {
        QProcess kb;
        kb.setProgram(binDir + QStringLiteral("/kbuildsycoca5"));
        kb.setArguments({QStringLiteral("--noincremental")});
        QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
        kb.setProcessEnvironment(env);
        kb.start();
        const bool finished = kb.waitForFinished(120000);
        check(finished && kb.exitStatus() == QProcess::NormalExit && kb.exitCode() == 0,
              "the packaged kbuildsycoca5 builds a sycoca database from the consumer's XDG tree");
        if (!finished || kb.exitCode() != 0) {
            std::printf("      kbuildsycoca5 rc=%d stderr=%s\n", kb.exitCode(),
                        QString::fromUtf8(kb.readAllStandardError()).toUtf8().constData());
        }

        const KService::Ptr found = KService::serviceByMenuId(QStringLiteral("ohos-consumer.desktop"));
        check(found && found->name() == QStringLiteral("OHOS Consumer Sample"),
              "KSycoca answers the menu-id lookup with the service the consumer installed");
        check(found && found->exec() == QStringLiteral("sample-app --flag"),
              "the looked-up service carries the Exec line from the .desktop file");

        // Now that a database exists, an unknown menu id must still resolve to
        // an empty result (rather than to someone else's service).
        const KService::Ptr missing =
            KService::serviceByMenuId(QStringLiteral("ohos-not-installed.desktop"));
        check(!missing, "an unknown menu id resolves to an empty KService");
    }

    // ---- Part 1: in-memory API on the installed package -------------------
    KService service(QStringLiteral("OHOS Sample"),
                     QStringLiteral("sample-app --flag"),
                     QStringLiteral("sample-icon"));
    check(service.isApplication() && service.name() == QStringLiteral("OHOS Sample") &&
              service.exec() == QStringLiteral("sample-app --flag") &&
              service.icon() == QStringLiteral("sample-icon"),
          "KService(name, exec, icon) round-trips through the accessors");

    KService other(QStringLiteral("OHOS Other"),
                   QStringLiteral("other-app"),
                   QStringLiteral("other-icon"));
    check(other.name() == QStringLiteral("OHOS Other") &&
              service.name() == QStringLiteral("OHOS Sample"),
          "a second KService keeps its own fields (no shared state)");

    KService copy(service);
    check(copy.exec() == service.exec() && copy.name() == service.name(),
          "the copy constructor preserves the parsed service");

    if (failures == 0) {
        std::printf("kservice consumer OK: all %d checks passed\n", total);
        return 0;
    }
    std::printf("kservice consumer: %d of %d checks FAILED\n", failures, total);
    return 1;
}
