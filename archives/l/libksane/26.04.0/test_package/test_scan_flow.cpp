/*
 * End-to-end consumer use case for libksane on HarmonyOS PC.
 *
 * A host application embeds KSaneWidget and drives one complete scanner
 * workflow, exactly as a real consumer would:
 *
 *   open device -> read device identity -> read option set ->
 *   write an option (resolution) -> select scan area -> start a final scan ->
 *   receive the scanned image from libksane -> close the device.
 *
 * The device is the SANE "frontend-tester" virtual scanner (backend `test`),
 * the official SANE device simulator for frontend validation. It performs a
 * real SANE transfer (sane_start/sane_read) and returns a real image, so the
 * whole libksane -> ksanecore -> libsane pipeline runs for real without
 * physical hardware.
 *
 * SPDX-License-Identifier: LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL
 */
#include <KSaneWidget>

#include <QApplication>
#include <QEventLoop>
#include <QImage>
#include <QMap>
#include <QPointF>
#include <QProcessEnvironment>
#include <QString>
#include <QStringList>
#include <QTimer>
#include <QtGlobal>

#include <cmath>
#include <cstdio>

namespace
{
int g_failures = 0;

void check(bool condition, const char *message)
{
    if (condition) {
        std::printf("PASS: %s\n", message);
    } else {
        std::printf("FAIL: %s\n", message);
        ++g_failures;
    }
}
}

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);

    KSaneIface::KSaneWidget widget;

    // A real consumer connects userMessage; otherwise libksane falls back to a
    // modal KMessageBox which cannot be answered in a headless run.
    QObject::connect(&widget, &KSaneIface::KSaneWidget::userMessage,
                     [](int, const QString &message) {
                         if (!message.isEmpty()) {
                             std::printf("INFO: libksane userMessage: %s\n",
                                         qUtf8Printable(message));
                         }
                     });

    // ---- Step 1: open the scanner ------------------------------------------
    // The SANE test backend names its virtual devices "0"/"1" when driven
    // directly; the dll loader prefixes them with the backend name ("test0").
    // Try both spellings so the flow works in either configuration.
    const QStringList candidates = {
        QStringLiteral("0"), QStringLiteral("test0"),
        QStringLiteral("1"), QStringLiteral("test1"),
    };
    QString openedDevice;
    for (const QString &candidate : candidates) {
        if (widget.openDevice(candidate)) {
            openedDevice = candidate;
            break;
        }
    }
    check(!openedDevice.isEmpty(), "host application opened a scanner device");
    if (openedDevice.isEmpty()) {
        std::printf("\nTESTS FAILED (no device could be opened)\n");
        return 1;
    }
    std::printf("INFO: opened device: %s\n", qUtf8Printable(openedDevice));

    // ---- Step 2: device identity ------------------------------------------
    check(widget.deviceName() == openedDevice,
          "deviceName() reports the device the application opened");
    // libksane fills deviceVendor()/deviceModel() only after a device-list
    // reload (the interactive device dialog path); report the values as
    // information instead of asserting on them in a headless run.
    std::printf("INFO: vendor=%s model=%s\n",
                qUtf8Printable(widget.deviceVendor()),
                qUtf8Printable(widget.deviceModel()));

    // ---- Step 3: real option set ------------------------------------------
    QMap<QString, QString> options;
    widget.getOptionValues(options);
    check(!options.isEmpty(), "the application reads the option set from the device");
    std::printf("INFO: option count: %d\n", int(options.size()));
    std::printf("INFO: options: %s\n", qUtf8Printable(QStringList(options.keys()).join(QLatin1Char(','))));

    // The backend's real option names prove the library is talking to a live
    // SANE device rather than returning canned values.
    check(options.contains(QStringLiteral("resolution")) && options.contains(QStringLiteral("mode")),
          "the device exposes its real SANE options (resolution, mode)");

    // ---- Step 4: write an option and read it back -------------------------
    check(widget.setOptionValue(QStringLiteral("resolution"), QStringLiteral("100")),
          "the application writes the scan resolution through libksane");
    QString readBack;
    const bool read = widget.getOptionValue(QStringLiteral("resolution"), readBack);
    check(read && readBack.startsWith(QStringLiteral("100")),
          "the written resolution is reported back by the device");
    std::printf("INFO: resolution read back: %s\n", qUtf8Printable(readBack));

    // ---- Step 5: scan area + a full scan ----------------------------------
    QImage scanned;
    int doneStatus = -1;
    QString doneMessage;
    bool scanDone = false;

    QObject::connect(&widget, &KSaneIface::KSaneWidget::scannedImageReady,
                     [&scanned](const QImage &image) { scanned = image; });

    QEventLoop loop;
    QObject::connect(&widget, &KSaneIface::KSaneWidget::scanDone,
                     [&](int status, const QString &message) {
                         doneStatus = status;
                         doneMessage = message;
                         scanDone = true;
                         loop.quit();
                     });

    // Full scanner area (the test backend exposes a 200x200 mm geometry).
    widget.setSelection(QPointF(0.0, 0.0), QPointF(80.0, 100.0));

    QTimer guard;
    guard.setSingleShot(true);
    QObject::connect(&guard, &QTimer::timeout, &loop, &QEventLoop::quit);
    guard.start(120000);

    widget.startScan();
    loop.exec();

    check(scanDone, "the scan completed within the timeout");
    check(doneStatus == KSaneIface::KSaneWidget::NoError,
          "libksane reported scan completion without error");
    if (doneStatus != KSaneIface::KSaneWidget::NoError && !doneMessage.isEmpty()) {
        std::printf("INFO: scanDone message: %s\n", qUtf8Printable(doneMessage));
    }
    check(!scanned.isNull() && scanned.width() > 0 && scanned.height() > 0,
          "libksane delivered a non-empty scanned image");
    std::printf("INFO: scanned image: %dx%d\n", scanned.width(), scanned.height());

    // 80x100 mm at 100 dpi -> the image must have the dimensions the
    // application asked for (the whole option/selection pipeline is honoured).
    const double expectedW = 80.0 / 25.4 * 100.0;
    const double expectedH = 100.0 / 25.4 * 100.0;
    check(scanned.width() > 0 && scanned.height() > 0
              && std::abs(scanned.width() - expectedW) <= expectedW * 0.08
              && std::abs(scanned.height() - expectedH) <= expectedH * 0.08,
          "the scanned image honours the requested area (80x100 mm) and resolution (100 dpi)");

    // Persist the result: the complete flow produced a real image artifact.
    if (!scanned.isNull()) {
        const QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
        QString dir = env.value(QStringLiteral("KSANE_TEST_ARTIFACT_DIR"));
        if (dir.isEmpty()) {
            dir = QStringLiteral(".");
        }
        const QString path = dir + QStringLiteral("/ksane-scan.png");
        check(scanned.save(path, "PNG"),
              "the scanned image was written to disk by the consumer application");
        std::printf("INFO: artifact: %s\n", qUtf8Printable(path));
    }

    // ---- Step 6: close the device -----------------------------------------
    check(widget.closeDevice(), "the host application closed the scanner device");
    check(widget.deviceName().isEmpty(), "deviceName() is cleared after closeDevice()");

    std::printf("\n%s (%d assertion(s) failed)\n",
                g_failures == 0 ? "ALL TESTS PASSED" : "TESTS FAILED", g_failures);
    return g_failures == 0 ? 0 : 1;
}
