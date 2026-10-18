/*  MystiQ - a C++/Qt5 gui frontend for ffmpeg
 *  HarmonyOS PC adaptation test.
 */

#include "testohosplatform.h"

#include <QGuiApplication>
#include <QStandardPaths>
#include <QProcess>

#include "../../services/notification.h"
#include "../../converter/exepath.h"

void TestOhosPlatform::testPlatformBackendIsHeadless()
{
    const QString platform = QGuiApplication::platformName();
    qDebug() << "QPA platform:" << platform;

    QVERIFY(!platform.isEmpty());
    QVERIFY2(!platform.contains("xcb"),
             "OHOS provides no X11 server: the xcb QPA plugin must not be in use");
    QVERIFY2(!platform.contains("wayland"),
             "OHOS target runs headless: wayland QPA plugin must not be in use");
    QVERIFY2(platform == "offscreen" || platform == "minimal" || platform == "vnc",
             qPrintable("unexpected QPA backend on OHOS: " + platform));
}

void TestOhosPlatform::testNotificationFallbackWithoutNotifySend()
{
    Notification::init();

    const QString notifySend = QStandardPaths::findExecutable("notify-send");
    const bool available = Notification::serviceAvailable(Notification::TYPE_NOTIFYSEND);
    qDebug() << "notify-send path:" << notifySend << "serviceAvailable:" << available;

    if (notifySend.isEmpty()) {
        /* OHOS: notify-send is absent, so TYPE_NOTIFYSEND must report unavailable
         * and setType() must refuse it (falling back to TYPE_MSGBOX). */
        QVERIFY2(!available, "TYPE_NOTIFYSEND must be unavailable when notify-send is missing");
        QVERIFY2(!Notification::setType(Notification::TYPE_NOTIFYSEND),
                 "setType(TYPE_NOTIFYSEND) must fall back to TYPE_MSGBOX");
    }

    /* MSGBOX backend is always available (pure Qt, no external dependency). */
    QVERIFY(Notification::serviceAvailable(Notification::TYPE_MSGBOX));

    Notification::release();
}

void TestOhosPlatform::testExternalProgramProbe()
{
    const QString sh = QStandardPaths::findExecutable("sh");
    QVERIFY2(!sh.isEmpty(), "sh must be resolvable through PATH on OHOS");
    qDebug() << "sh path:" << sh;

    ExePath::setPath("sh", sh);
    QCOMPARE(ExePath::getPath("sh"), sh);

    /* mystiq starts ffmpeg/ffprobe/sox with QProcess; on OHOS hmdfs this fails
     * when the binary is not executable, so probe a known-good native binary. */
    QVERIFY2(ExePath::checkProgramAvailability("sh"),
             "QProcess must be able to start a native OHOS binary (hmdfs noexec check)");
}

QTEST_MAIN(TestOhosPlatform)
