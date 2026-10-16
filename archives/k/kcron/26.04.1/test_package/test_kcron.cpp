// kcron 26.04.1 consumer test (R34: exercises the real shipped artifacts).
//
// The KCM cannot be *shown* without a full Plasma session, so the consumer
// verification drives the shipped artifacts the way the platform loads them:
//   CASE 1  package contents: kcm_cron.so, kcron_helper and the generated
//           kcm_cron.desktop are located inside the installed package tree
//           (KAuth activation files are reported when present);
//   CASE 2  QPluginLoader loads kcm_cron.so and reads its metadata;
//   CASE 3  KPluginFactory::instantiatePlugin<QObject> creates the KCMCron
//           instance exactly the way KCMUtils does (superclass-chain match
//           against the QObject interface). On hosts where the current uid
//           has no /etc/passwd entry the captured qCWarning must be the
//           patched "No password entry found for uid" CTInitializationError
//           path instead of a crash (patch 0004);
//   CASE 4  the tasksModel/variablesModel properties expose the models and a
//           null current-user cron is tolerated (patches 0005/0006 - reaching
//           this point at all proves the constructor's refresh(nullptr)
//           survived);
//   CASE 5  the full QML task-validation flow through a real QQmlEngine
//           (module org.kde.private.kcms.cron): @reboot task with an empty
//           command is invalid ("Choose a program to run"), a real
//           executable passes, a missing absolute path fails with
//           "File not found";
//   CASE 6  clipboard paste on both models with a null cron must not crash
//           (patch 0005/0006 guards);
//   CASE 7  load()/defaults()/refreshPages() and the isPersonalUse
//           round-trip (its setter calls refreshCron()).
//
// print()/save()/applyCreate() are deliberately not called: they open the
// interactive file dialog or dereference the current cron in the KCM slots
// (documented limitation in the recipe docstring).
#include <QAbstractItemModel>
#include <QApplication>
#include <QClipboard>
#include <QDir>
#include <QDirIterator>
#include <QFileInfo>
#include <QJsonObject>
#include <QMetaType>
#include <QPluginLoader>
#include <QQmlComponent>
#include <QQmlContext>
#include <QQmlEngine>
#include <QUrl>
#include <QVariant>

#include <KPluginFactory>
#include <KPluginMetaData>

#include <pwd.h>
#include <unistd.h>

#include <cstdio>

static int g_failures = 0;

static void check(bool ok, const char *name)
{
    std::printf("[test] %s %s\n", ok ? "PASS" : "FAIL", name);
    if (!ok) {
        ++g_failures;
    }
}

static void info(const char *name, const QString &detail)
{
    std::printf("[test] INFO %s: %s\n", name, qPrintable(detail));
}

static QString findInPackage(const QString &root, const QString &fileName)
{
    QDirIterator it(root, QDir::Files | QDir::NoDotAndDotDot,
                    QDirIterator::Subdirectories);
    while (it.hasNext()) {
        it.next();
        if (it.fileName() == fileName) {
            return it.filePath();
        }
    }
    return QString();
}

static QStringList g_messages;

static void captureHandler(QtMsgType, const QMessageLogContext &, const QString &message)
{
    g_messages.append(message);
}

// A real executable for the positive validation case; the same list the
// upstream test style uses (an absolute path is required for the
// "File not found" negative case to be meaningful).
static QString firstRunnableCommand()
{
    const QStringList candidates = {
        QStringLiteral("/bin/sh"),
        QStringLiteral("/usr/bin/ls"),
        QStringLiteral("/bin/ls"),
        QStringLiteral("/system/bin/sh"),
        QStringLiteral("/usr/bin/true"),
    };
    for (const QString &candidate : candidates) {
        const QFileInfo info(candidate);
        if (info.exists() && info.isExecutable()) {
            return candidate;
        }
    }
    return QStringLiteral("sh"); // bare fallback resolves through PATH
}

template<typename T>
static T *propertyCast(QObject *object, const char *name)
{
    QVariant value = object->property(name);
    if (!value.isValid()) {
        return nullptr;
    }
    if (value.metaType().id() != QMetaType::QObjectStar) {
        // QObject-derived pointer (TasksModel*/VariablesModel*): let the
        // metatype system upcast it to QObject*.
        if (!value.convert(QMetaType(QMetaType::QObjectStar))) {
            // Documented fallback: for pointer metatypes QVariant stores the
            // pointer value itself, and QObject-derived pointers are
            // layout-compatible with QObject* for this null/upcast check.
            return value.constData()
                ? *reinterpret_cast<T *const *>(value.constData())
                : nullptr;
        }
    }
    return value.value<T *>();
}

int main(int argc, char **argv)
{
    QApplication app(argc, argv);
    if (argc < 2) {
        std::fprintf(stderr, "usage: test_kcron <kcron package dir>\n");
        return 2;
    }
    const QString packageDir = QString::fromLocal8Bit(argv[1]);
    std::printf("[test] INFO package dir: %s\n", qPrintable(packageDir));

    // ── CASE 1: installed artifacts ────────────────────────────────────
    const QString pluginPath = findInPackage(packageDir, QStringLiteral("kcm_cron.so"));
    const QString helperPath = findInPackage(packageDir, QStringLiteral("kcron_helper"));
    const QString desktopPath = findInPackage(packageDir, QStringLiteral("kcm_cron.desktop"));
    const QString policyPath = findInPackage(packageDir, QStringLiteral("local.kcron.crontab.policy"));
    const QString actionsPath = findInPackage(packageDir, QStringLiteral("local.kcron.crontab.actions"));
    check(!pluginPath.isEmpty(), "CASE 1a kcm_cron.so present in package");
    check(!helperPath.isEmpty(), "CASE 1b kcron_helper present in package");
    check(!desktopPath.isEmpty(), "CASE 1c generated kcm_cron.desktop present in package");
    if (!pluginPath.isEmpty()) {
        info("CASE 1d plugin", QDir(packageDir).relativeFilePath(pluginPath));
    }
    if (!policyPath.isEmpty() || !actionsPath.isEmpty()) {
        info("CASE 1e KAuth activation files",
             QStringLiteral("policy=%1 actions=%2")
                 .arg(policyPath.isEmpty() ? QStringLiteral("(none)") : QDir(packageDir).relativeFilePath(policyPath),
                      actionsPath.isEmpty() ? QStringLiteral("(none)") : QDir(packageDir).relativeFilePath(actionsPath)));
    } else {
        info("CASE 1e KAuth activation files", QStringLiteral("not installed (KAuth backend dependent)"));
    }

    if (pluginPath.isEmpty()) {
        std::printf("[test] FAIL incomplete package, aborting\n");
        return 1;
    }

    // ── CASE 2: QPluginLoader ──────────────────────────────────────────
    QPluginLoader loader(pluginPath);
    const bool loaded = loader.load();
    check(loaded, "CASE 2a QPluginLoader loads kcm_cron.so");
    if (loaded) {
        const QJsonObject metaData = loader.metaData();
        check(!metaData.isEmpty(), "CASE 2b QPluginLoader metadata readable");
        info("CASE 2c plugin metadata",
             QStringLiteral("className=%1 iid=%2")
                 .arg(metaData.value(QStringLiteral("className")).toString(),
                      metaData.value(QStringLiteral("IID")).toString()));
    } else {
        info("CASE 2 error", loader.errorString());
    }

    // ── CASE 3: KPluginFactory instantiation (KCMUtils load path) ──────
    {
        g_messages.clear();
        qInstallMessageHandler(captureHandler);
        auto result = KPluginFactory::instantiatePlugin<QObject>(KPluginMetaData(pluginPath), &app);
        qInstallMessageHandler(nullptr);
        QObject *plugin = result.plugin;
        check(plugin != nullptr, "CASE 3a KPluginFactory instantiates the KCM (QObject iface match)");
        if (!plugin) {
            info("CASE 3 error", result.errorString);
            std::printf("[test] FAILURES PRESENT (%d failure(s))\n", g_failures);
            return 1;
        }

        // On hosts where the current uid has no /etc/passwd entry the patched
        // CTHost path must produce its CTInitializationError (captured from
        // the qCWarning in KCMCron::init) and keep the module alive.
        const bool passwdMissing = getpwuid(getuid()) == nullptr;
        const QString joined = g_messages.join(QLatin1Char('\n'));
        info("CASE 3b init messages", joined.isEmpty() ? QStringLiteral("(none)") : joined);
        if (passwdMissing) {
            check(joined.contains(QStringLiteral("An error occurred while creating the CTHost object")),
                  "CASE 3c no-passwd host: patched CTHost error path reached");
            check(joined.contains(QStringLiteral("No password entry found for uid")),
                  "CASE 3d no-passwd host: CTInitializationError message surfaced");
        } else {
            info("CASE 3c host has a passwd entry", QStringLiteral("adaptive checks skipped"));
        }

        // ── CASE 4: models ─────────────────────────────────────────────
        QObject *tasksModel = propertyCast<QObject>(plugin, "tasksModel");
        QObject *variablesModel = propertyCast<QObject>(plugin, "variablesModel");
        check(tasksModel != nullptr, "CASE 4a tasksModel property exposes the model");
        check(variablesModel != nullptr, "CASE 4b variablesModel property exposes the model");
        auto *tasks = qobject_cast<QAbstractItemModel *>(tasksModel);
        auto *variables = qobject_cast<QAbstractItemModel *>(variablesModel);
        check(tasks != nullptr, "CASE 4c tasks model is a QAbstractItemModel");
        check(variables != nullptr, "CASE 4d variables model is a QAbstractItemModel");
        if (tasks) {
            info("CASE 4e task rows", QString::number(tasks->rowCount()));
        }
        if (variables) {
            info("CASE 4f variable rows", QString::number(variables->rowCount()));
        }
        if (passwdMissing) {
            check(tasks && tasks->rowCount() == 0,
                  "CASE 4g no-passwd host: empty task model under a null cron");
            check(variables && variables->rowCount() == 0,
                  "CASE 4h no-passwd host: empty variable model under a null cron");
        }

        // ── CASE 5: QML task-validation flow ───────────────────────────
        const QString testCommand = firstRunnableCommand();
        info("CASE 5a test command", testCommand);

        QQmlEngine engine;
        engine.rootContext()->setContextProperty(QStringLiteral("tasksModel"), tasksModel);
        engine.rootContext()->setContextProperty(QStringLiteral("testCommand"), testCommand);

        static const char *qmlSource = R"QML(
import QtQml
import org.kde.private.kcms.cron 1.0

QtObject {
    id: root
    property bool ran: false
    property bool emptyInvalid: false
    property bool filledValid: false
    property bool missingInvalid: false
    property string errorText: ""

    property TaskValidator validator: TaskValidator {
    }

    function run() {
        var tmp = tasksModel.create()
        validator.task = tmp
        root.emptyInvalid = (!validator.validate())
            && (validator.errorString.indexOf("Choose a program to run") >= 0)
        tmp.reboot = true
        tmp.command = testCommand
        root.filledValid = validator.validate()
        tmp.command = "/no/such/binary-xyz"
        root.missingInvalid = !validator.validate()
        root.errorText = validator.errorString
        root.ran = true
    }
}
)QML";

        QQmlComponent component(&engine);
        component.setData(QByteArray(qmlSource), QUrl(QStringLiteral("qrc:/test_kcron.qml")));
        QObject *rootObject = component.create();
        if (!rootObject) {
            check(false, "CASE 5b QML component instantiates");
            info("CASE 5 errors", component.errorString());
        } else {
            check(true, "CASE 5b QML component instantiates (module + TaskValidator)");
            QMetaObject::invokeMethod(rootObject, "run");
            check(rootObject->property("ran").toBool(), "CASE 5c QML run() completed");
            check(rootObject->property("emptyInvalid").toBool(),
                  "CASE 5d empty command rejected (Choose a program to run)");
            check(rootObject->property("filledValid").toBool(),
                  "CASE 5e real executable validates");
            check(rootObject->property("missingInvalid").toBool(),
                  "CASE 5f missing absolute path rejected");
            const QString errorText = rootObject->property("errorText").toString();
            check(errorText.contains(QStringLiteral("File not found")),
                  "CASE 5g errorString reports File not found");
            info("CASE 5h errorString", errorText);
            delete rootObject;  // component.create() hands over ownership
        }

        // ── CASE 6: clipboard paste guards with a null cron ────────────
        QClipboard *clipboard = QApplication::clipboard();
        if (clipboard) {
            clipboard->setText(QStringLiteral("TEST=1"));
            const bool pastedTasks = QMetaObject::invokeMethod(tasksModel, "paste");
            const bool pastedVariables = QMetaObject::invokeMethod(variablesModel, "paste");
            check(pastedTasks && pastedVariables, "CASE 6a paste invokables callable on both models");
        } else {
            info("CASE 6 clipboard", QStringLiteral("no clipboard on this platform, skipped"));
        }

        // ── CASE 7: non-interactive invokables + property round-trip ───
        const bool loadOk = QMetaObject::invokeMethod(plugin, "load");
        const bool defaultsOk = QMetaObject::invokeMethod(plugin, "defaults");
        const bool pagesOk = QMetaObject::invokeMethod(plugin, "refreshPages");
        check(loadOk && defaultsOk && pagesOk,
              "CASE 7a load()/defaults()/refreshPages() run without crash");
        const QVariant initial = plugin->property("isPersonalUse");
        check(initial.isValid() && initial.toBool(), "CASE 7b isPersonalUse defaults to true");
        plugin->setProperty("isPersonalUse", false);
        const bool switched = !plugin->property("isPersonalUse").toBool();
        plugin->setProperty("isPersonalUse", true);
        check(switched && plugin->property("isPersonalUse").toBool(),
              "CASE 7c isPersonalUse round-trips (setter refresh path)");
        const QVariant userList = plugin->property("userList");
        check(userList.isValid() && userList.metaType().id() == QMetaType::QStringList,
              "CASE 7d userList readable");
    }

    std::printf("[test] %s (%d failure(s))\n",
                g_failures == 0 ? "ALL CONSUMER CASES PASSED" : "FAILURES PRESENT",
                g_failures);
    return g_failures == 0 ? 0 : 1;
}
