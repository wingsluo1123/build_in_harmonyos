// kparts 6.14.0 consumer test (R34: exercises real API).
// Verifies the KParts::PartManager can be constructed with a top-level widget
// and that a new manager has no registered parts.
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
    std::printf("PASS: KParts::PartManager constructed OK\n");
    return 0;
}
