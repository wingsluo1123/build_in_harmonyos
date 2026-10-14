/*
 * Consumer-side functional test for libksane 26.04.0 on HarmonyOS PC.
 *
 * The test links the installed KSaneWidgets6 library, constructs the
 * KSaneIface::KSaneWidget offscreen (which exercises the whole widget tree plus
 * the KSaneCore6 backend object) and asserts the documented behaviour of the
 * public API when no scanner device is open. No scanner hardware is required.
 */
#include <KSaneWidget>

#include <QApplication>
#include <QMap>
#include <QPushButton>
#include <QString>

#include <cstdio>

static int g_failures = 0;

static void check(bool condition, const char *message)
{
    if (condition) {
        std::printf("PASS: %s\n", message);
    } else {
        std::printf("FAIL: %s\n", message);
        ++g_failures;
    }
}

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);

    KSaneIface::KSaneWidget widget;

    // The object was really constructed from the installed library (not a stub).
    check(QString::fromLatin1(widget.metaObject()->className())
              == QStringLiteral("KSaneIface::KSaneWidget"),
          "KSaneWidget instance has the expected runtime class name");

    // The widget builds its whole UI in the constructor: the preview/scan
    // buttons must exist.
    check(widget.findChildren<QPushButton *>().size() >= 2,
          "KSaneWidget builds its UI (scan/preview buttons present)");

    // No device is open: the device metadata accessors stay empty.
    check(widget.deviceName().isEmpty(), "deviceName() is empty without an open device");
    check(widget.deviceVendor().isEmpty(), "deviceVendor() is empty without an open device");
    check(widget.deviceModel().isEmpty(), "deviceModel() is empty without an open device");

    // Closing a device that was never opened reports failure.
    check(!widget.closeDevice(), "closeDevice() returns false without an open device");

    // The scan area is only known once a device is open.
    check(widget.scanAreaWidth() == 0.0f, "scanAreaWidth() is 0 without an open device");
    check(widget.scanAreaHeight() == 0.0f, "scanAreaHeight() is 0 without an open device");

    // Option accessors are inert without a device.
    QString value;
    check(!widget.getOptionValue(QStringLiteral("resolution"), value),
          "getOptionValue() returns false without an open device");
    check(!widget.setOptionValue(QStringLiteral("resolution"), QStringLiteral("300")),
          "setOptionValue() returns false without an open device");

    QMap<QString, QString> options;
    widget.getOptionValues(options);
    check(options.isEmpty(), "getOptionValues() yields an empty map without an open device");

    QMap<QString, QString> writeOptions;
    writeOptions.insert(QStringLiteral("resolution"), QStringLiteral("300"));
    check(widget.setOptionValues(writeOptions) == -1,
          "setOptionValues() returns -1 without an open device");

    // scan slots are callable and harmless while idle: cancelScan() must not
    // start a scan nor change the (device-less) observable state.
    widget.cancelScan();
    check(!widget.isVisible() && widget.deviceName().isEmpty(),
          "cancelScan() is callable while idle and leaves the state unchanged");

    // The widget is not shown by the consumer.
    check(!widget.isVisible(), "KSaneWidget is not visible unless shown");

    std::printf("\n%s (%d assertion(s) failed)\n",
                g_failures == 0 ? "ALL TESTS PASSED" : "TESTS FAILED", g_failures);
    return g_failures == 0 ? 0 : 1;
}
