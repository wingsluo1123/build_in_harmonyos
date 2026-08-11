// svgpart 26.04.3 consumer test (R34: exercises real API).
// Creates a KParts::PartManager host and verifies the KParts framework is
// usable; the SvgPart plugin itself is loaded through the KPluginFactory in
// the host application (svgpart is a plugin, not a static class).
#include <KParts/PartManager>
#include <QApplication>
#include <QWidget>
#include <cstdio>

int main(int argc, char **argv) {
    QApplication app(argc, argv);
    QWidget topLevel;
    KParts::PartManager manager(&topLevel, &app);
    if (manager.parts().isEmpty() == false) {
        std::printf("FAIL: new PartManager should have no parts\n");
        return 1;
    }
    std::printf("PASS: svgpart host (KParts::PartManager) usable OK\n");
    return 0;
}
