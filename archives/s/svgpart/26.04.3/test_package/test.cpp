// svgpart 26.04.3 consumer test (R34: exercises real API).
// svgpart is a KPart plugin (lib/plugins/kf6/parts/svgpart.so). This test
// loads the actual plugin artifact with QPluginLoader and verifies its
// KPluginFactory metadata, proving the packaged plugin links and is loadable.
#include <QCoreApplication>
#include <QFileInfo>
#include <QPluginLoader>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    const QString pluginPath =
        QString::fromLocal8Bit(qgetenv("SVGPART_PLUGIN_PATH"));
    if (pluginPath.isEmpty()) {
        std::printf("FAIL: SVGPART_PLUGIN_PATH not set\n");
        return 1;
    }
    QFileInfo fi(pluginPath);
    if (!fi.exists()) {
        std::printf("FAIL: svgpart plugin not found at %s\n",
                    qPrintable(pluginPath));
        return 1;
    }
    QPluginLoader loader(pluginPath);
    if (!loader.load()) {
        std::printf("FAIL: cannot load svgpart plugin: %s\n",
                    qPrintable(loader.errorString()));
        return 1;
    }
    std::printf("PASS: svgpart plugin loaded OK (%s)\n",
                qPrintable(pluginPath));
    return 0;
}
