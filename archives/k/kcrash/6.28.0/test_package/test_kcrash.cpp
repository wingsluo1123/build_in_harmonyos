// kcrash 6.28.0 consumer test (R34: exercises the real API).
//
// Five consumer-level cases against the published package:
//   1. DrKonqi toggle surface: isDrKonqiEnabled() starts disabled, disabling
//      is idempotent, and requesting it stays disabled because the
//      implementation falls back when no drkonqi executable exists in the
//      search paths (there is none on OHOS).
//   2. Crash-handler surface: setEmergencySaveFunction installs the default
//      crash handler and both getters report the installed values.
//   3. Error-information setters are callable (setErrorMessage, setErrorTags,
//      setErrorExtraData, setGPUData).
//   4. E2E: the child consumer process crashes with SIGSEGV while an
//      emergency save function installed through the public API is active;
//      the function runs inside the KCrash crash handler and its output is
//      durable in the log file.
//   5. E2E: the child consumer process crashes with AutoRestart |
//      AlwaysDirectly; KCrash re-executes it as a second instance which runs
//      to normal completion.
#include <KCrash>

#include <QByteArray>
#include <QCoreApplication>
#include <QFile>
#include <QProcess>
#include <QString>
#include <QStringList>
#include <QTemporaryDir>
#include <QThread>

#include <cstdio>

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

static void consumerSaveFunction(int)
{
}

static bool caseDrKonqiToggle(QString *detail)
{
    if (KCrash::isDrKonqiEnabled()) {
        *detail = QStringLiteral("DrKonqi reported enabled before any request");
        return false;
    }
    KCrash::setDrKonqiEnabled(false);
    if (KCrash::isDrKonqiEnabled()) {
        *detail = QStringLiteral("DrKonqi still enabled after setDrKonqiEnabled(false)");
        return false;
    }
    // No drkonqi executable exists on OHOS, so the implementation must fall
    // back to disabled even when enabling is requested.
    KCrash::setDrKonqiEnabled(true);
    if (KCrash::isDrKonqiEnabled()) {
        *detail = QStringLiteral("DrKonqi reported enabled although no drkonqi executable exists");
        return false;
    }
    return true;
}

static bool caseCrashHandlerSurface(QString *detail)
{
    if (KCrash::emergencySaveFunction() != nullptr) {
        *detail = QStringLiteral("emergency save function not null on a fresh process");
        return false;
    }
    KCrash::setEmergencySaveFunction(consumerSaveFunction);
    if (KCrash::emergencySaveFunction() != consumerSaveFunction) {
        *detail = QStringLiteral("emergencySaveFunction() does not report the installed function");
        return false;
    }
    if (KCrash::crashHandler() != KCrash::defaultCrashHandler) {
        *detail = QStringLiteral("setEmergencySaveFunction did not install the default crash handler");
        return false;
    }
    KCrash::setEmergencySaveFunction(nullptr);
    if (KCrash::emergencySaveFunction() != nullptr) {
        *detail = QStringLiteral("emergency save function not cleared by nullptr");
        return false;
    }
    return true;
}

static bool caseErrorInformationSetters(QString *detail)
{
    Q_UNUSED(detail)
    // The four setters return void and have no getters; the case verifies
    // that the exported symbols resolve and the calls complete against the
    // packaged library.
    KCrash::setErrorMessage(QStringLiteral("consumer test error message"));
    KCrash::setErrorTags({{QStringLiteral("consumer"), QStringLiteral("kcrash")}});
    KCrash::setErrorExtraData({{QStringLiteral("consumer"), QStringLiteral("kcrash")}});
    KCrash::setGPUData({{QStringLiteral("name"), QStringLiteral("consumer-test")}});
    return true;
}

static QByteArray readLogFile(const QString &path)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) {
        return QByteArray();
    }
    return file.readAll();
}

static bool runCrasherToLog(const QString &flag, const QByteArray &expected, QString *detail)
{
    const QString crasher = QCoreApplication::applicationDirPath() + QStringLiteral("/consumer_crasher");
    if (!QFile::exists(crasher)) {
        *detail = QStringLiteral("consumer_crasher not found next to the test binary: %1").arg(crasher);
        return false;
    }

    QTemporaryDir tmp;
    if (!tmp.isValid()) {
        *detail = QStringLiteral("cannot create a temporary directory");
        return false;
    }
    const QString logPath = tmp.filePath(QStringLiteral("crasher.log"));

    QProcess proc;
    proc.setProcessChannelMode(QProcess::ForwardedChannels);
    proc.start(crasher, QStringList{flag, logPath});
    if (!proc.waitForStarted(30000)) {
        *detail = QStringLiteral("consumer_crasher failed to start: %1").arg(proc.errorString());
        return false;
    }
    // The crashing instance dies from the signal; in the autorestart case a
    // second instance started by KCrash writes the final line slightly later.
    if (!proc.waitForFinished(60000)) {
        proc.kill();
        proc.waitForFinished(5000);
        *detail = QStringLiteral("consumer_crasher did not terminate");
        return false;
    }

    QByteArray data = readLogFile(logPath);
    for (int i = 0; i < 100 && data != expected; ++i) {
        QThread::msleep(100);
        data = readLogFile(logPath);
    }
    if (data != expected) {
        *detail = QStringLiteral("log content '%1' (exitStatus %2, exitCode %3), expected '%4'")
                      .arg(QString::fromUtf8(data))
                      .arg(int(proc.exitStatus()))
                      .arg(proc.exitCode())
                      .arg(QString::fromUtf8(expected));
        return false;
    }
    return true;
}

static bool caseEmergencySaveE2E(QString *detail)
{
    return runCrasherToLog(QStringLiteral("ES"),
                           QByteArray("starting ES\nsaveFunction called\n"),
                           detail);
}

static bool caseAutoRestartE2E(QString *detail)
{
    return runCrasherToLog(QStringLiteral("ARD"),
                           QByteArray("starting ARD\nautorestarted ARD\n"),
                           detail);
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    const struct {
        const char *name;
        bool (*run)(QString *);
    } cases[] = {
        {"api-drkonqi-toggle", caseDrKonqiToggle},
        {"api-crash-handler-surface", caseCrashHandlerSurface},
        {"api-error-information-setters", caseErrorInformationSetters},
        {"e2e-emergency-save-on-crash", caseEmergencySaveE2E},
        {"e2e-autorestart-directly", caseAutoRestartE2E},
    };

    for (const auto &testCase : cases) {
        QString detail;
        report(testCase.run(&detail), testCase.name, detail);
    }

    std::printf("TEST SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
