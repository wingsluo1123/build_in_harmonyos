// kconfig 6.28.0 consumer test — KConfig XT case.
//
// The sources of this executable are generated at build time by the
// packaged kconfig_compiler, driven through the installed
// kconfig_add_kcfg_files CMake function (kcfg/xttest.kcfgc -> xttest.h/.cpp).
// The generated KconfigXtTest skeleton must produce the declared defaults,
// save values and reload them in a fresh instance.
#include "xttest.h"

#include <QCoreApplication>
#include <QFile>
#include <QStandardPaths>
#include <QString>

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

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // The suite may run more than once (ctest round plus direct execution)
    // against the same XDG_CONFIG_HOME; drop the file written by earlier
    // runs so the generated-defaults check is deterministic.
    const QString configDir = QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation);
    QFile::remove(configDir + QLatin1String("/kconfigxttest_rc"));

    {
        KconfigXtTest config;
        const bool defaultsOk = config.name() == QLatin1String("unset") && config.volume() == 42;
        report(defaultsOk,
               "xt-defaults",
               defaultsOk ? QString()
                          : QStringLiteral("generated defaults are name='%1' volume=%2")
                                .arg(config.name())
                                .arg(config.volume()));
        config.setName(QStringLiteral("kconfig-xt"));
        config.setVolume(77);
        report(config.save(), "xt-save", QStringLiteral("KConfigSkeleton::save() failed"));
    }
    {
        KconfigXtTest reread;
        reread.load();
        const bool reloadOk = reread.name() == QLatin1String("kconfig-xt") && reread.volume() == 77;
        report(reloadOk,
               "xt-reload",
               reloadOk ? QString()
                        : QStringLiteral("reloaded name='%1' volume=%2")
                              .arg(reread.name())
                              .arg(reread.volume()));
    }

    std::printf("TEST SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
