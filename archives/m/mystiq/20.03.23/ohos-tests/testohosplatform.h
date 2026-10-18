/*  MystiQ - a C++/Qt5 gui frontend for ffmpeg
 *  HarmonyOS PC adaptation test: platform backend, notification fallback,
 *  external program probing.
 */

#ifndef TESTOHOSPLATFORM_H
#define TESTOHOSPLATFORM_H

#include <QtTest/QtTest>

class TestOhosPlatform : public QObject
{
    Q_OBJECT
private slots:
    /* OHOS has no X11/Wayland: the QPA backend must be headless. */
    void testPlatformBackendIsHeadless();
    /* notify-send is not shipped on OHOS: the notification subsystem must fall back. */
    void testNotificationFallbackWithoutNotifySend();
    /* ffmpeg/ffprobe/sox are started through QProcess: probing must work on OHOS. */
    void testExternalProgramProbe();
};

#endif // TESTOHOSPLATFORM_H
