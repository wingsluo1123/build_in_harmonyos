// kconfig 6.28.0 consumer test (R34: exercises the real API).
//
// Runs six consumer-level cases against the published package:
//   1. KConfig/KConfigGroup round-trip through a SimpleConfig file
//   2. KSharedConfig persistence, verified through the raw file on disk
//   3. KCoreConfigSkeleton typed items (defaults, save, reload)
//   4. kwriteconfig6/kreadconfig6 command line tools round-trip
//   5. KWindowConfig save/restore on a QWindow (offscreen platform)
//   6. the shipped org.kde.config QML module inside a QQmlEngine,
//      cross-checked between the QML KAuthorized singleton and the C++ API
#include <KAuthorized>
#include <KConfig>
#include <KConfigGroup>
#include <KCoreConfigSkeleton>
#include <KSharedConfig>
#include <KWindowConfig>

#include <QDir>
#include <QEventLoop>
#include <QFile>
#include <QGuiApplication>
#include <QProcess>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QStandardPaths>
#include <QString>
#include <QTimer>
#include <QWindow>

#include <cstdio>
#include <memory>

static int g_passed = 0;
static int g_failed = 0;

static void report(const bool ok, const char *name, const QString &detail)
{
    if (ok) {
        ++g_passed;
        std::printf("TEST PASS: %s\n", name);
    } else {
        ++g_failed;
        std::printf("TEST FAIL: %s%s\n", name,
                    detail.isEmpty() ? "" : (" -- " + detail).toUtf8().constData());
    }
}

// The suite may run more than once (ctest round plus direct execution)
// against the same XDG_CONFIG_HOME; remove the files written by earlier runs
// so the default-value and first-write checks are deterministic.
static void resetConfigState()
{
    const QString dir = QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation);
    const char *names[] = {
        "kconfigtest_rc",
        "kconfigtest_shared_rc",
        "kconfigtest_skeleton_rc",
        "kconfigtest_cli_rc",
        "kconfigtest_window_rc",
    };
    for (const char *name : names) {
        QFile::remove(dir + QLatin1Char('/') + QLatin1String(name));
    }
}

// Deterministic kiosk gating for the QML case: the restriction is written
// before any KConfig object is created so shell_access is denied and ghns
// keeps its default (allowed).
static void applyKioskGating()
{
    const QString dir = QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation);
    QDir().mkpath(dir);
    QFile file(dir + QLatin1String("/kdeglobals"));
    if (file.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
        file.write("[KDE Action Restrictions]\nshell_access=false\n");
        file.close();
    }
}

static bool caseConfigGroupRoundtrip(QString *detail)
{
    KConfig config(QStringLiteral("kconfigtest_rc"), KConfig::SimpleConfig);
    config.group(QStringLiteral("General")).writeEntry(QStringLiteral("name"), QStringLiteral("world"));
    config.sync();

    KConfig reread(QStringLiteral("kconfigtest_rc"), KConfig::SimpleConfig);
    const QString value = reread.group(QStringLiteral("General")).readEntry("name", QString());
    if (value != QLatin1String("world")) {
        *detail = QStringLiteral("round-trip returned '%1'").arg(value);
        return false;
    }
    return true;
}

static bool caseSharedConfigPersistence(QString *detail)
{
    KSharedConfig::Ptr shared = KSharedConfig::openConfig(QStringLiteral("kconfigtest_shared_rc"));
    shared->group(QStringLiteral("Shared")).writeEntry(QStringLiteral("value"), 123);
    shared->sync();

    const int back = shared->group(QStringLiteral("Shared")).readEntry(QStringLiteral("value"), -1);
    if (back != 123) {
        *detail = QStringLiteral("KSharedConfig returned %1").arg(back);
        return false;
    }
    // name() returns the config name as passed; the file lives below
    // XDG_CONFIG_HOME (GenericConfigLocation), so build the absolute path.
    const QString configDir = QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation);
    QFile raw(configDir + QLatin1String("/kconfigtest_shared_rc"));
    if (!raw.open(QIODevice::ReadOnly)) {
        *detail = QStringLiteral("cannot read %1").arg(raw.fileName());
        return false;
    }
    if (!raw.readAll().contains("value=123")) {
        *detail = QStringLiteral("raw file %1 lacks the written entry").arg(raw.fileName());
        return false;
    }
    return true;
}

class CountSkeleton : public KCoreConfigSkeleton
{
public:
    CountSkeleton()
        : KCoreConfigSkeleton(QStringLiteral("kconfigtest_skeleton_rc"))
        , m_count(0)
        , m_label()
    {
        addItemInt(QStringLiteral("count"), m_count, 7);
        addItemString(QStringLiteral("label"), m_label, QStringLiteral("default-label"));
    }

    qint32 m_count;
    QString m_label;
};

static bool caseSkeletonTyped(QString *detail)
{
    {
        CountSkeleton skeleton;
        if (skeleton.m_count != 7 || skeleton.m_label != QLatin1String("default-label")) {
            *detail = QStringLiteral("defaults are count=%1 label=%2")
                          .arg(skeleton.m_count)
                          .arg(skeleton.m_label);
            return false;
        }
        skeleton.m_count = 99;
        skeleton.m_label = QStringLiteral("written");
        if (!skeleton.save()) {
            *detail = QStringLiteral("KCoreConfigSkeleton::save() failed");
            return false;
        }
    }
    {
        CountSkeleton reread;
        reread.load();
        if (reread.m_count != 99 || reread.m_label != QLatin1String("written")) {
            *detail = QStringLiteral("reload returned count=%1 label=%2")
                          .arg(reread.m_count)
                          .arg(reread.m_label);
            return false;
        }
    }
    return true;
}

static bool caseCliTools(QString *detail)
{
    const QString writer = qEnvironmentVariable("KWRITECONFIG6_BIN");
    const QString reader = qEnvironmentVariable("KREADCONFIG6_BIN");
    if (writer.isEmpty() || reader.isEmpty()) {
        *detail = QStringLiteral("KWRITECONFIG6_BIN/KREADCONFIG6_BIN not set by the runner");
        return false;
    }
    const QStringList common{QStringLiteral("--file"),
                             QStringLiteral("kconfigtest_cli_rc"),
                             QStringLiteral("--group"),
                             QStringLiteral("CLI"),
                             QStringLiteral("--key"),
                             QStringLiteral("key")};

    QProcess write;
    write.start(writer, common + QStringList{QStringLiteral("cli-value")});
    if (!write.waitForFinished(60000) || write.exitStatus() != QProcess::NormalExit || write.exitCode() != 0) {
        *detail = QStringLiteral("kwriteconfig6 failed: %1")
                      .arg(QString::fromLocal8Bit(write.readAllStandardError()).trimmed());
        return false;
    }

    QProcess read;
    read.start(reader, common);
    if (!read.waitForFinished(60000) || read.exitStatus() != QProcess::NormalExit || read.exitCode() != 0) {
        *detail = QStringLiteral("kreadconfig6 failed: %1")
                      .arg(QString::fromLocal8Bit(read.readAllStandardError()).trimmed());
        return false;
    }
    const QString value = QString::fromLocal8Bit(read.readAllStandardOutput()).trimmed();
    if (value != QLatin1String("cli-value")) {
        *detail = QStringLiteral("kreadconfig6 returned '%1'").arg(value);
        return false;
    }
    return true;
}

static bool caseWindowConfig(QString *detail)
{
    QWindow window;
    window.resize(640, 480);
    window.show();
    if (!window.screen()) {
        *detail = QStringLiteral("offscreen window has no screen");
        return false;
    }

    KConfig config(QStringLiteral("kconfigtest_window_rc"), KConfig::SimpleConfig);
    KConfigGroup group = config.group(QStringLiteral("Window"));
    KWindowConfig::saveWindowSize(&window, group);
    config.sync();

    KConfig rereadConfig(QStringLiteral("kconfigtest_window_rc"), KConfig::SimpleConfig);
    KConfigGroup rereadGroup = rereadConfig.group(QStringLiteral("Window"));
    if (!KWindowConfig::hasSavedWindowSize(rereadGroup)) {
        *detail = QStringLiteral("no saved window size in the group");
        return false;
    }

    QWindow restored;
    restored.resize(100, 100);
    restored.show();
    KWindowConfig::restoreWindowSize(&restored, rereadGroup);
    if (restored.size() != QSize(640, 480)) {
        *detail = QStringLiteral("restored %1x%2, expected 640x480")
                      .arg(restored.size().width())
                      .arg(restored.size().height());
        return false;
    }
    return true;
}

static bool caseQmlModule(QString *detail)
{
    QQmlEngine engine;
    QQmlComponent component(&engine);
    component.setData("import QtQml\n"
                      "import org.kde.config\n"
                      "QtObject {\n"
                      "    property bool shellAccess: KAuthorized.authorize(\"shell_access\")\n"
                      "    property bool ghns: KAuthorized.authorize(\"ghns\")\n"
                      "}\n",
                      QUrl(QStringLiteral("inmemory:/consumer.qml")));
    // QML module and plugin loading can complete asynchronously; wait for
    // the component to leave the Loading state (bounded) before creating it.
    if (component.isLoading()) {
        QEventLoop loop;
        QObject::connect(&component, &QQmlComponent::statusChanged, &loop, &QEventLoop::quit);
        QTimer::singleShot(30000, &loop, &QEventLoop::quit);
        loop.exec();
    }
    if (!component.isReady()) {
        *detail = QStringLiteral("component not ready (status %1): %2")
                      .arg(int(component.status()))
                      .arg(component.errorString());
        return false;
    }
    std::unique_ptr<QObject> object(component.create());
    if (!object) {
        *detail = QStringLiteral("org.kde.config instantiation failed: %1").arg(component.errorString());
        return false;
    }

    const bool qmlShell = object->property("shellAccess").toBool();
    const bool qmlGhns = object->property("ghns").toBool();
    const bool cppShell = KAuthorized::authorize(QStringLiteral("shell_access"));
    const bool cppGhns = KAuthorized::authorize(QStringLiteral("ghns"));

    if (qmlShell || !qmlGhns) {
        *detail = QStringLiteral("KAuthorized from QML returned shell_access=%1 ghns=%2")
                      .arg(int(qmlShell))
                      .arg(int(qmlGhns));
        return false;
    }
    if (qmlShell != cppShell || qmlGhns != cppGhns) {
        *detail = QStringLiteral("QML/C++ KAuthorized mismatch (shell %1/%2, ghns %3/%4)")
                      .arg(int(qmlShell))
                      .arg(int(cppShell))
                      .arg(int(qmlGhns))
                      .arg(int(cppGhns));
        return false;
    }
    return true;
}

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);
    resetConfigState();
    applyKioskGating();

    const struct {
        const char *name;
        bool (*run)(QString *);
    } cases[] = {
        {"config-group-roundtrip", caseConfigGroupRoundtrip},
        {"shared-config-persistence", caseSharedConfigPersistence},
        {"skeleton-typed-roundtrip", caseSkeletonTyped},
        {"cli-tools-kwriteconfig-kreadconfig", caseCliTools},
        {"window-config-save-restore", caseWindowConfig},
        {"qml-org-kde-config-kauthorized", caseQmlModule},
    };

    for (const auto &testCase : cases) {
        QString detail;
        report(testCase.run(&detail), testCase.name, detail);
    }

    std::printf("TEST SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
