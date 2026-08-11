// kjobwidgets 6.14.0 consumer test (R34: exercises real API).
// KAbstractWidgetJobTracker is abstract; use the concrete KStatusBarJobTracker.
#include <KStatusBarJobTracker>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    KStatusBarJobTracker tracker;
    std::printf("PASS: KStatusBarJobTracker constructed OK\n");
    return 0;
}
