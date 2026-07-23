#include <ElaWidget.h>
#include <QApplication>
#include <QCoreApplication>

int main(int argc, char *argv[]) {
    // Use offscreen platform to avoid display server dependency
    qputenv("QT_QPA_PLATFORM", "offscreen");

    QApplication app(argc, argv);

    // Test: create an ElaWidget instance (calls ElaWidgetTools API)
    ElaWidget widget;
    widget.setWindowTitle("ElaWidgetTools Test");

    // Verify the widget was created
    if (widget.windowTitle() != "ElaWidgetTools Test") {
        return 1;
    }

    return 0;
}
