// test_kwidgetsaddons.cpp — Verify KF6WidgetsAddons library links and API works
#include <KCapacityBar>
#include <QApplication>
#include <cstdio>

int main(int argc, char *argv[]) {
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QApplication app(argc, argv);
    KCapacityBar bar;
    bar.setValue(42);
    if (bar.value() == 42) {
        printf("kwidgetsaddons test: KF6WidgetsAddons linked and KCapacityBar API functional\n");
        return 0;
    }
    fprintf(stderr, "kwidgetsaddons test: value mismatch\n");
    return 1;
}
