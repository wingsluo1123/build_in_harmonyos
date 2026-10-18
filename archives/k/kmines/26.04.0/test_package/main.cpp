#include <QByteArray>
#include <QFile>
#include <QFileInfo>
#include <QGuiApplication>
#include <QList>
#include <QPixmap>
#include <QProcess>
#include <QSize>
#include <QString>
#include <cstdio>
#include <cstdlib>
#include <sys/wait.h>

#include <KGameRenderer>
#include <KGameTheme>
#include <KGameThemeProvider>

// kmines is an application package: the R34-relevant consumer
// verification is running the installed deliverable and exercising the
// runtime data path the game itself uses at startup. Four cases:
//
//   1. installed_binary_version - run bin/kmines --version offscreen,
//      require exit code 0 and the upstream 4.0.26040 version string
//      (KMINES_VERSION = "4.0." + the unpadded release-service compact
//      version 26/04/0).
//   2. theme_discovery         - KGameThemeProvider::discoverThemes(
//      "themes") must find the six themes installed into
//      share/kmines/themes via QStandardPaths::AppDataLocation; every
//      theme's graphicsPath must be an existing gzip-compressed SVGZ.
//   3. theme_sprite_render     - KGameRenderer::spritePixmap("mainWidget")
//      renders the default theme through the real SVGZ -> QSvgRenderer ->
//      QPixmap pipeline that KMines' QGraphicsScene drives.
//   4. app_boot                - start bin/kmines offscreen with an
//      isolated HOME and require the startup path to make progress: the
//      process either stays alive for five seconds, or — on images with
//      no DBus session bus — exits with the exact KDBusAddons "DBus
//      session bus not found" diagnostic, which proves the ELF/Qt/KF6
//      loader chain completed. Any other early exit fails the case.
//
// Every case emits an independent TEST PASS / TEST FAIL line; the final
// TEST SUMMARY line counts them and main() exits 1 if any case failed.

static int gPassed = 0;
static int gFailed = 0;

static void report(const char *name, bool ok)
{
    if (ok) {
        ++gPassed;
        std::printf("TEST PASS: %s\n", name);
    } else {
        ++gFailed;
        std::printf("TEST FAIL: %s\n", name);
    }
}

static bool caseBinaryVersion(const QString &exe)
{
    if (!QFileInfo(exe).isExecutable()) {
        std::printf("  installed binary missing or not executable: %s\n",
                    qPrintable(exe));
        return false;
    }
    const QString cmd = QStringLiteral("\"%1\" --version 2>&1").arg(exe);
    FILE *p = ::popen(cmd.toUtf8().constData(), "r");
    if (!p) {
        std::printf("  popen failed for %s\n", qPrintable(exe));
        return false;
    }
    QByteArray out;
    char buf[512];
    while (::fgets(buf, sizeof buf, p)) {
        out += buf;
    }
    // pclose() returns a wait status, not an exit code: decode it so the
    // logged value is the process status the case actually gates on.
    const int status = ::pclose(p);
    const int rc = WIFEXITED(status) ? WEXITSTATUS(status) : -1;
    std::printf("  kmines --version rc=%d output=%s\n", rc,
                out.trimmed().constData());
    // KMINES_VERSION = "4.0." + RELEASE_SERVICE_COMPACT_VERSION, and the
    // compact version concatenates 26/04/0 without zero padding, so the
    // installed binary reports "4.0.26040".
    return rc == 0 && out.contains("kmines") && out.contains("4.0.26040");
}

static bool caseThemeDiscovery()
{
    KGameThemeProvider provider;
    provider.discoverThemes(QStringLiteral("themes"));
    const QList<const KGameTheme *> themes = provider.themes();
    std::printf("  discovered %lld themes\n",
                static_cast<long long>(themes.size()));

    if (themes.size() != 6) {
        std::printf("  expected the six installed themes "
                    "(default/classic/green/graveyard-mayhem/"
                    "clean_blue/clean_blue_dark)\n");
        return false;
    }

    bool ok = true;
    for (const KGameTheme *theme : themes) {
        const QString graphics = theme->graphicsPath();
        QFile f(graphics);
        bool valid = f.exists() && f.size() > 1000;
        bool gzipMagic = false;
        if (valid && f.open(QIODevice::ReadOnly)) {
            const QByteArray magic = f.read(3);
            gzipMagic = magic.size() == 3
                && static_cast<unsigned char>(magic.at(0)) == 0x1f
                && static_cast<unsigned char>(magic.at(1)) == 0x8b
                && static_cast<unsigned char>(magic.at(2)) == 0x08;
            f.close();
        }
        std::printf("  theme %s name='%s' graphics=%s size=%lld gzip=%d\n",
                    qPrintable(theme->identifier()),
                    qPrintable(theme->name()),
                    qPrintable(graphics),
                    static_cast<long long>(f.size()),
                    gzipMagic ? 1 : 0);
        ok = ok && !theme->name().isEmpty() && valid && gzipMagic;
    }
    return ok;
}

static bool caseThemeSpriteRender(KGameThemeProvider *provider)
{
    bool exists = false;
    bool pixmapOk = false;
    int pixmapW = 0;
    int pixmapH = 0;
    {
        KGameRenderer renderer(provider);
        exists = renderer.spriteExists(QStringLiteral("mainWidget"));
        const QPixmap pixmap =
            renderer.spritePixmap(QStringLiteral("mainWidget"), QSize(64, 64));
        pixmapW = pixmap.width();
        pixmapH = pixmap.height();
        pixmapOk = !pixmap.isNull();
        std::printf("  spriteExists(mainWidget)=%d pixmap=%dx%d null=%d\n",
                    exists ? 1 : 0, pixmapW, pixmapH,
                    pixmapOk ? 0 : 1);
    }
    return exists && pixmapOk && pixmapW == 64 && pixmapH == 64;
}

static bool caseAppBoot(const QString &exe)
{
    QProcess proc;
    proc.setProcessChannelMode(QProcess::MergedChannels);
    proc.start(exe, QStringList());
    if (!proc.waitForStarted(15000)) {
        std::printf("  failed to start %s: %s\n", qPrintable(exe),
                    qPrintable(proc.errorString()));
        return false;
    }
    // waitForFinished() runs the process machinery and keeps draining the
    // merged channel while it waits. A bare sleep followed by state() can
    // miss an early crash (no event loop pumps the child-exit notification)
    // and a full stderr pipe would stall the child into looking alive.
    const bool exitedEarly = proc.waitForFinished(5000);
    // Qt: waitForFinished() also returns false when the process has already
    // finished; state() distinguishes that from a real timeout, otherwise an
    // early crash between waitForStarted() and this call would be read as
    // "alive" and the case would pass without any loader evidence.
    const bool alive = !exitedEarly && proc.state() != QProcess::NotRunning;
    QByteArray out = proc.readAll();
    if (alive) {
        proc.kill();
        proc.waitForFinished(5000);
        out += proc.readAll();
    } else {
        std::printf("  process exited early: rc=%d\n", proc.exitCode());
    }
    std::printf("  alive after 5s=%d, captured %lld bytes of output\n",
                alive ? 1 : 0, static_cast<long long>(out.size()));
    if (!out.isEmpty()) {
        std::printf("  output: %s\n", out.left(600).constData());
    }
    if (alive) {
        return true;
    }
    // This HarmonyOS image ships no DBus session bus and no dbus-launch, so
    // KDBusService aborts every KF6 GUI right after Qt/KF6 initialisation.
    // Reaching that exact diagnostic still proves the whole ELF/Qt/KF6
    // loader chain succeeded; a missing library or plugin fails earlier
    // with different output, so only this exact message is accepted.
    const bool busMissing = out.contains("DBus session bus not found");
    if (busMissing) {
        std::printf("  environment has no DBus session bus; startup "
                    "verified through the KDBusAddons initialisation\n");
    }
    return busMissing;
}

int main(int argc, char **argv)
{
    // Unbuffered stdout: conan captures the output through a pipe, which
    // would otherwise turn every printf into a block-buffered write and
    // lose the per-case verdicts if a later stage crashes.
    std::setvbuf(stdout, nullptr, _IONBF, 0);

    QGuiApplication app(argc, argv);
    // QStandardPaths::AppDataLocation must resolve to share/kmines; the
    // binary under test is named kmines, but set it explicitly so the
    // test binary name never leaks into the lookup.
    QCoreApplication::setApplicationName(QStringLiteral("kmines"));
    QCoreApplication::setApplicationVersion(QStringLiteral("4.0.26040"));

    // qgetenv returns an empty QByteArray for unset variables; passing a
    // null getenv() result straight to fromUtf8 is undefined behaviour.
    const QString exe = QString::fromUtf8(qgetenv("KMINES_TEST_BIN"));
    const QString data = QString::fromUtf8(qgetenv("KMINES_TEST_DATA"));
    if (exe.isEmpty() || data.isEmpty()) {
        std::printf("KMINES_TEST_BIN / KMINES_TEST_DATA not set\n");
        return 1;
    }
    std::printf("=== kmines consumer test ===\n");
    std::printf("binary: %s\ndata: %s\n", qPrintable(exe),
                qPrintable(data));

    report("installed_binary_version", caseBinaryVersion(exe));

    const bool discoveryOk = caseThemeDiscovery();
    report("theme_discovery", discoveryOk);

    if (discoveryOk) {
        // Only render when discovery succeeded; the renderer needs a
        // selected default theme and would otherwise just repeat the
        // discovery failure. Upstream KMinesScene builds its provider
        // with "new KGameThemeProvider" and hands it to KGameRenderer,
        // which reparents and later deletes a parentless provider. A
        // stack provider here would be deleted through a stack pointer
        // during renderer teardown, so mirror the upstream ownership.
        KGameThemeProvider *provider = new KGameThemeProvider;
        provider->discoverThemes(QStringLiteral("themes"));
        report("theme_sprite_render", caseThemeSpriteRender(provider));
    } else {
        std::printf("  skipping theme_sprite_render (discovery failed)\n");
        report("theme_sprite_render", false);
    }

    report("app_boot", caseAppBoot(exe));

    std::printf("TEST SUMMARY: %d passed, %d failed\n", gPassed, gFailed);
    return gFailed == 0 ? 0 : 1;
}
