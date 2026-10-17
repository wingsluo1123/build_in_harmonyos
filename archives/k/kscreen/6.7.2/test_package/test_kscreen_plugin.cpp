/*
    SPDX-FileCopyrightText: 2026 The OHOS port contributors

    SPDX-License-Identifier: GPL-2.0-or-later

    Consumer test for the kscreen 6.7.2 OHOS package.

    Two real executions, no stubs:
      1. QPluginLoader against the packaged kded plugin
         (lib/plugins/kf6/kded/kscreen.so): load(), factory instantiation
         and the embedded KPlugin metadata (IID org.kde.KPluginFactory,
         KPlugin.Version 6.7.2, X-KDE-Kded-autoload true). This is the
         exact consumption path of the kded daemon and it exercises the
         SONAME-less KF6 runtime dependencies of the plugin.
      2. QProcess against the packaged kscreen-console (--help) with the
         offscreen QPA platform: exit 0 plus usage output.

    Every check prints a TEST PASS line; the first failure prints TEST FAIL
    and exits 1 so `conan create` fails loudly.
*/
#include <QCoreApplication>
#include <QFileInfo>
#include <QJsonObject>
#include <QJsonValue>
#include <QPluginLoader>
#include <QProcess>
#include <QString>
#include <QStringList>
#include <QVariant>

#include <cstdio>
#include <cstdlib>

static int g_checksPassed = 0;

static void pass(const QString &what)
{
    ++g_checksPassed;
    std::printf("TEST PASS: %s\n", qUtf8Printable(what));
    std::fflush(stdout);
}

static void fail(const QString &what)
{
    std::printf("TEST FAIL: %s\n", qUtf8Printable(what));
    std::fflush(stdout);
    std::exit(1);
}

static QString firstExisting(const QStringList &candidates)
{
    for (const QString &candidate : candidates) {
        if (QFileInfo::exists(candidate)) {
            return candidate;
        }
    }
    return QString();
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    QString pkg = argc > 1 ? QString::fromLocal8Bit(argv[1]) : QString();
    if (pkg.isEmpty()) {
        pkg = qEnvironmentVariable("KS_TESTED_PACKAGE_FOLDER");
    }
    if (pkg.isEmpty()) {
        fail("tested package folder not provided (argv[1] or KS_TESTED_PACKAGE_FOLDER)");
    }
    std::printf("kscreen package under test: %s\n", qUtf8Printable(pkg));
    std::printf("Qt runtime: %s\n", qUtf8Printable(qVersion()));

    // ---- 1. packaged kded plugin: dlopen + metadata --------------------
    const QString plugin = firstExisting({
        pkg + QStringLiteral("/lib/plugins/kf6/kded/kscreen.so"),
        pkg + QStringLiteral("/plugins/kf6/kded/kscreen.so"),
    });
    if (plugin.isEmpty()) {
        fail(QStringLiteral("kscreen kded plugin not found under %1").arg(pkg));
    }
    pass(QStringLiteral("kded plugin located: %1").arg(plugin));

    QPluginLoader loader(plugin);
    if (!loader.load()) {
        fail(QStringLiteral("QPluginLoader::load() failed: %1").arg(loader.errorString()));
    }
    pass(QStringLiteral("QPluginLoader::load() succeeded (dlopen + Qt plugin ABI)"));

    const QJsonObject metaData = loader.metaData();
    const QString iid = metaData.value(QStringLiteral("IID")).toString();
    if (iid != QLatin1String("org.kde.KPluginFactory")) {
        fail(QStringLiteral("plugin IID mismatch: %1").arg(iid));
    }
    pass(QStringLiteral("embedded IID is org.kde.KPluginFactory"));

    const QJsonObject inner = metaData.value(QStringLiteral("MetaData")).toObject();
    const QString version = inner.value(QStringLiteral("KPlugin")).toObject()
                                .value(QStringLiteral("Version")).toString();
    if (version != QLatin1String("6.7.2")) {
        fail(QStringLiteral("KPlugin.Version mismatch: %1").arg(version));
    }
    pass(QStringLiteral("embedded KPlugin.Version is 6.7.2"));

    const QJsonValue autoload = inner.value(QStringLiteral("X-KDE-Kded-autoload"));
    if (!(autoload == QJsonValue(true) || autoload.toString() == QLatin1String("true"))) {
        fail(QStringLiteral("X-KDE-Kded-autoload is not true: %1").arg(autoload.toString()));
    }
    pass(QStringLiteral("embedded X-KDE-Kded-autoload is true"));

    if (loader.instance() == nullptr) {
        fail(QStringLiteral("plugin factory instantiation failed: %1").arg(loader.errorString()));
    }
    pass(QStringLiteral("KPluginFactory instance created from the packaged plugin"));
    // The loader keeps ownership of the live instance; unload() is not
    // called with instances outstanding.

    // ---- 2. packaged kscreen-console: --help E2E -----------------------
    const QString console = firstExisting({
        pkg + QStringLiteral("/bin/kscreen-console"),
        pkg + QStringLiteral("/libexec/kscreen-console"),
    });
    if (console.isEmpty()) {
        fail(QStringLiteral("kscreen-console binary not found under %1").arg(pkg));
    }
    pass(QStringLiteral("kscreen-console located: %1").arg(console));

    QProcess proc;
    proc.setProcessChannelMode(QProcess::MergedChannels);
    proc.start(console, {QStringLiteral("--help")});
    if (!proc.waitForFinished(60000)) {
        fail(QStringLiteral("kscreen-console --help timed out"));
    }
    const QString output = QString::fromUtf8(proc.readAll());
    std::printf("kscreen-console --help exit=%d, output:\n%s\n",
                proc.exitCode(), qUtf8Printable(output));
    if (proc.exitStatus() != QProcess::NormalExit || proc.exitCode() != 0) {
        fail(QStringLiteral("kscreen-console --help exit code %1").arg(proc.exitCode()));
    }
    pass(QStringLiteral("kscreen-console --help exited 0 (offscreen QPA, QGuiApplication alive)"));
    if (!output.contains(QLatin1String("kscreen-console"))) {
        fail(QStringLiteral("kscreen-console --help output does not mention the program name"));
    }
    pass(QStringLiteral("kscreen-console --help printed usage output"));

    std::printf("ALL CHECKS PASSED (%d)\n", g_checksPassed);
    return 0;
}
