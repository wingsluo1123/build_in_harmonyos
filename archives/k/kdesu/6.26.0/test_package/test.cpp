// kdesu 6.26.0 consumer test (R34: exercises real API).
//
// - the exported KF6Su package resolves and KF6::Su links
// - SuProcess reads the super-user-command configuration (default su, sudo,
//   doas and the unknown-value fallback) and useUsersOwnPassword() honours the
//   sudo/doas root semantics
// - SshProcess constructs and exposes its (empty) prompt state
// - the installed kdesu_stub helper answers the protocol installation check
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QProcess>
#include <QtGlobal>

#include <KConfigGroup>
#include <KSharedConfig>

#include <KDESu/SshProcess>
#include <KDESu/SuProcess>

#include <cstdio>

static int failures = 0;

static void check(bool condition, const char *what)
{
    if (condition) {
        std::printf("PASS: %s\n", what);
    } else {
        std::printf("FAIL: %s\n", what);
        ++failures;
    }
}

static void setSuperUserCommand(const QString &value)
{
    KSharedConfig::Ptr config = KSharedConfig::openConfig();
    KConfigGroup group(config, QStringLiteral("super-user-command"));
    group.writeEntry(QStringLiteral("super-user-command"), value);
    config->sync();
}

int main(int argc, char **argv)
{
    // The device's /tmp is not writable; use a private directory under $HOME
    // unless the caller (conan test) already provided one.
    if (qEnvironmentVariableIsEmpty("XDG_CONFIG_HOME")) {
        const QString fallback = QDir::homePath() + QStringLiteral("/.kdesu-consumer-test-config");
        QDir().mkpath(fallback);
        qputenv("XDG_CONFIG_HOME", QFile::encodeName(fallback));
    }

    QCoreApplication app(argc, argv);
    QCoreApplication::setApplicationName(QStringLiteral("kdesu-consumer-test"));

    // 1. Default: no configuration entry -> upstream default is su.
    {
        KDESu::SuProcess su(QByteArray("root"), QByteArray("true"));
        check(su.superUserCommand() == QLatin1String("su"),
              "default super-user-command is su");
    }

    // 2. sudo is read back and the sudo root semantics hold.
    {
        setSuperUserCommand(QStringLiteral("sudo"));
        KDESu::SuProcess su(QByteArray("root"), QByteArray("true"));
        check(su.superUserCommand() == QLatin1String("sudo"),
              "super-user-command sudo is read back");
        check(su.useUsersOwnPassword(),
              "sudo + root asks for the user's own password");
    }

    // 3. doas is read back.
    {
        setSuperUserCommand(QStringLiteral("doas"));
        KDESu::SuProcess su(QByteArray("root"), QByteArray("true"));
        check(su.superUserCommand() == QLatin1String("doas"),
              "super-user-command doas is read back");
    }

    // 4. An unknown value falls back to the compiled-in default (su).
    {
        setSuperUserCommand(QStringLiteral("kdesu-test-unknown"));
        KDESu::SuProcess su(QByteArray("root"), QByteArray("true"));
        check(su.superUserCommand() == QLatin1String("su"),
              "unknown super-user-command falls back to su");
    }

    // 5. SshProcess is part of the same library and constructs cleanly.
    {
        KDESu::SshProcess ssh(QByteArray("example.invalid"), QByteArray("nobody"), QByteArray("true"));
        check(ssh.prompt().isEmpty(), "SshProcess starts with an empty prompt");
    }

#ifdef KDESU_TEST_STUB_PATH
    // 6. The installed kdesu_stub helper speaks the protocol installation
    //    check: it prompts "kdesu_stub", and answering "stop" must exit 0
    //    after printing the "end" marker.
    {
        QProcess stub;
        stub.start(QStringLiteral(KDESU_TEST_STUB_PATH), QStringList());
        check(stub.waitForStarted(10000), "kdesu_stub starts");
        stub.write("stop\n");
        stub.closeWriteChannel();
        const bool finished = stub.waitForFinished(10000);
        check(finished, "kdesu_stub finishes after stop");
        if (finished) {
            const QByteArray out = stub.readAllStandardOutput();
            check(stub.exitStatus() == QProcess::NormalExit && stub.exitCode() == 0,
                  "kdesu_stub exits 0 on installation check");
            check(out.contains("kdesu_stub") && out.contains("end"),
                  "kdesu_stub prints the protocol prompt and end marker");
        }
    }
#endif

    std::printf("failures=%d\n", failures);
    return failures == 0 ? 0 : 1;
}
