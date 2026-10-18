// kcrash 6.28.0 consumer crasher -- deliberately crashes a child process for
// the E2E cases in test_kcrash.
//
// Usage: consumer_crasher <ES|ARD> <log-file>
//   ES  : installs an emergency save function through the public API, then
//         crashes with SIGSEGV; the function must run from inside the KCrash
//         crash handler even though the process dies.
//   ARD : requests AutoRestart | AlwaysDirectly, then crashes; KCrash
//         re-executes this program as a second instance with
//         KCRASH_AUTO_RESTARTED=1, which logs the "autorestarted" line and
//         exits normally.
#include <KCrash>

#include <QCoreApplication>
#include <QFile>
#include <QStringList>

#include <cstdio>

#ifdef Q_OS_UNIX
#include <sys/resource.h>
#endif

static QFile *s_output = nullptr;

static void saveFunction(int)
{
    if (s_output) {
        s_output->write("saveFunction called\n");
        s_output->flush();
    }
}

int main(int argc, char **argv)
{
    // Mirror the upstream kcrashtest strategy: KDE_DEBUG makes
    // KCrash::initialize() skip DrKonqi plumbing while still preparing the
    // autorestart command line, so the crash handler exercised here is the
    // one installed by setEmergencySaveFunction()/setFlags().
    qputenv("KDE_DEBUG", "1");
    QCoreApplication app(argc, argv);

    KCrash::initialize();

    const QStringList args = app.arguments();
    if (args.size() < 3) {
        std::fprintf(stderr, "usage: consumer_crasher <ES|ARD> <log-file>\n");
        return 2;
    }
    const QByteArray flag = args.at(1).toLatin1();

    if (flag == "ES") {
        KCrash::setEmergencySaveFunction(saveFunction);
    } else if (flag == "ARD") {
        KCrash::setFlags(KCrash::AutoRestart | KCrash::AlwaysDirectly);
    } else {
        std::fprintf(stderr, "unknown flag %s\n", flag.constData());
        return 2;
    }

#ifdef Q_OS_UNIX
    // No core file, same as the upstream test_crasher.
    struct rlimit rlp;
    rlp.rlim_cur = 0;
    rlp.rlim_max = 0;
    setrlimit(RLIMIT_CORE, &rlp);
#endif

    QFile output(args.at(2));
    s_output = &output;
    if (!output.open(QIODevice::WriteOnly | QIODevice::Append)) {
        std::fprintf(stderr, "cannot open %s\n", qPrintable(args.at(2)));
        return 1;
    }

    if (qEnvironmentVariableIsEmpty("KCRASH_AUTO_RESTARTED")) {
        output.write("starting ");
        output.write(flag);
        output.write("\n");
        output.flush();
        // CRASH!
        delete (char *)0xdead;
    } else {
        output.write("autorestarted ");
        output.write(flag);
        output.write("\n");
        output.close();
    }
    return 0;
}
