// kiconthemes 6.28.0 consumer end-to-end test (R34: real API usage).
// Installs a tiny icon theme into an isolated XDG data directory before the
// application starts, then exercises the public KIconLoader, KIconTheme and
// KIconEngine APIs against it. Each case reports TEST PASS/FAIL and any
// failure makes the process exit with status 1.
#include <KIconEngine>
#include <KIconLoader>
#include <KIconTheme>
#include <QApplication>
#include <QDir>
#include <QFile>
#include <QIcon>
#include <QImage>
#include <QPixmap>
#include <QStringList>
#include <cstdio>

static int checks = 0;
static int failures = 0;

static void check(const char *name, bool ok)
{
    ++checks;
    if (!ok) {
        ++failures;
    }
    std::printf("TEST %s: %s\n", ok ? "PASS" : "FAIL", name);
    std::fflush(stdout);
}

static bool write_file(const QString &path, const QByteArray &contents)
{
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
        return false;
    }
    const bool ok = file.write(contents) == contents.size();
    file.close();
    return ok;
}

int main(int argc, char **argv)
{
    // Isolated XDG home: the icon theme and the KDE icon setting are fully
    // test-owned so the result does not depend on the host installation.
    const QString base = QDir::currentPath() + QStringLiteral("/test-xdg");
    const QString iconDir = base + QStringLiteral("/icons/kit-test/32x32/apps");
    const QString cacheDir = base + QStringLiteral("/cache");
    QDir().mkpath(iconDir);
    QDir().mkpath(cacheDir);

    QImage image(32, 32, QImage::Format_ARGB32_Premultiplied);
    image.fill(Qt::red);
    const bool pngOk = image.save(iconDir + QStringLiteral("/kit-test-icon.png"));
    const bool themeOk = write_file(
        base + QStringLiteral("/icons/kit-test/index.theme"),
        QByteArray("[Icon Theme]\n"
                   "Name=Kit Test\n"
                   "Directories=32x32/apps\n"
                   "\n"
                   "[32x32/apps]\n"
                   "Size=32\n"
                   "Context=Applications\n"
                   "Type=Fixed\n"));
    const bool configOk = write_file(
        base + QStringLiteral("/kdeglobals"),
        QByteArray("[Icons]\n"
                   "Theme=kit-test\n"));

    qputenv("XDG_DATA_HOME", base.toUtf8());
    qputenv("XDG_CONFIG_HOME", base.toUtf8());
    qputenv("XDG_CACHE_HOME", cacheDir.toUtf8());
    qputenv("QT_QPA_PLATFORM", QByteArray("offscreen"));

    QApplication app(argc, argv);
    // The application name is part of KIconLoader's theme configuration.
    QApplication::setApplicationName(QStringLiteral("kit-test"));

    check("icon theme fixture written", pngOk && themeOk && configOk);

    KIconLoader *loader = KIconLoader::global();
    check("KIconLoader::global available", loader != nullptr);
    if (!loader) {
        std::printf("TEST SUMMARY: %d/%d passed, %d failed\n", checks - failures, checks, failures);
        return 1;
    }

    const KIconTheme *activeTheme = loader->theme();
    check("KIconLoader resolves configured theme",
          activeTheme != nullptr && activeTheme->internalName() == QStringLiteral("kit-test"));

    KIconTheme theme(QStringLiteral("kit-test"));
    check("KIconTheme constructed from disk", theme.isValid());
    // queryIcons() returns full file paths for the theme's icon directories,
    // so look for the installed icon file rather than a bare icon name.
    bool enumerated = false;
    const QStringList icons = theme.queryIcons();
    for (const QString &entry : icons) {
        if (entry.endsWith(QStringLiteral("/kit-test-icon.png"))) {
            enumerated = true;
            break;
        }
    }
    check("KIconTheme enumerates installed icon", enumerated);

    const QPixmap pixmap = loader->loadIcon(QStringLiteral("kit-test-icon"),
                                            KIconLoader::NoGroup, 32);
    check("KIconLoader::loadIcon returns a pixmap", !pixmap.isNull());
    check("KIconLoader::loadIcon keeps the requested size",
          !pixmap.isNull() && pixmap.width() == 32 && pixmap.height() == 32);

    const QPixmap missing = loader->loadIcon(QStringLiteral("kit-test-missing-icon"),
                                             KIconLoader::NoGroup, 32);
    check("unknown icon resolves to null pixmap", missing.isNull());

    KIconEngine engine(QStringLiteral("kit-test-icon"), loader);
    const QPixmap enginePixmap = engine.pixmap(QSize(32, 32), QIcon::Normal, QIcon::Off);
    check("KIconEngine::pixmap returns a pixmap", !enginePixmap.isNull());

    std::printf("TEST SUMMARY: %d/%d passed, %d failed\n",
                checks - failures, checks, failures);
    return failures == 0 ? 0 : 1;
}
