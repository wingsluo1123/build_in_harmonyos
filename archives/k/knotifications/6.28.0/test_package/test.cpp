// Consumer smoke test for the knotifications/6.28.0 HarmonyOS PC package.
// Exercises the public API of the shipped libKF6Notifications.so: the
// KNotification property surface (eventId/title/text/icon/flags/urgency/
// componentName/hints/urls/autoDelete) and the KNotificationAction model
// (R34: real API usage, no stubs).
// The version header installs directly at the exported include root
// (include/KF6/KNotifications/knotifications_version.h, see the
// INSTALL_INTERFACE of the KF6Notifications target).
#include <KNotification>
#include <knotifications_version.h>

#include <QByteArray>
#include <QCoreApplication>
#include <QList>
#include <QString>
#include <QUrl>
#include <QVariantMap>

#include <cstdio>

static int g_passed = 0;
static int g_failed = 0;

static void report(const char *name, bool ok, const QByteArray &debug = QByteArray())
{
    if (ok) {
        ++g_passed;
        std::printf("TEST PASS: %s\n", name);
    } else {
        ++g_failed;
        std::printf("TEST FAIL: %s\n", name);
        if (!debug.isEmpty()) {
            std::printf("--- debug artifact ---\n%s\n--- end debug artifact ---\n",
                        debug.constData());
        }
    }
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // 1) Version binding: the packaged headers report the 6.28.0 version.
    report("version header reports 6.28.0",
           QString::fromLatin1(KNOTIFICATIONS_VERSION_STRING)
               == QStringLiteral("6.28.0"));

    // 2) Constructor + eventId round-trip.
    KNotification *n = new KNotification(QStringLiteral("ohpcd-test"));
    report("eventId round-trip after construction",
           n->eventId() == QStringLiteral("ohpcd-test"));

    // 3) title/text round-trip.
    n->setTitle(QStringLiteral("Hello"));
    n->setText(QStringLiteral("World"));
    report("title/text round-trip",
           n->title() == QStringLiteral("Hello")
               && n->text() == QStringLiteral("World"));

    // 4) iconName round-trip.
    n->setIconName(QStringLiteral("dialog-information"));
    report("iconName round-trip",
           n->iconName() == QStringLiteral("dialog-information"));

    // 5) flags round-trip (CloseOnTimeout = 0x00, Persistent = 0x02).
    n->setFlags(KNotification::CloseOnTimeout | KNotification::Persistent);
    report("flags round-trip",
           n->flags() == (KNotification::CloseOnTimeout
                          | KNotification::Persistent));

    // 6) urgency round-trip (LowUrgency = 10, CriticalUrgency = 90).
    n->setUrgency(KNotification::LowUrgency);
    const bool lowOk = n->urgency() == KNotification::LowUrgency;
    n->setUrgency(KNotification::CriticalUrgency);
    report("urgency set/get round-trip (Low, Critical)",
           lowOk && n->urgency() == KNotification::CriticalUrgency);

    // 7) componentName round-trip.
    n->setComponentName(QStringLiteral("knotifications-ohpc-test"));
    report("componentName round-trip",
           n->componentName() == QStringLiteral("knotifications-ohpc-test"));

    // 8) hints round-trip (QVariantMap).
    const QVariantMap hints{
        {QStringLiteral("x-kde-test"), QStringLiteral("value-1")},
    };
    n->setHints(hints);
    report("hints map round-trip",
           n->hints().value(QStringLiteral("x-kde-test")).toString()
               == QStringLiteral("value-1"),
           n->hints().value(QStringLiteral("x-kde-test")).toString().toUtf8());

    // 9) urls round-trip (QList<QUrl>).
    const QList<QUrl> urls{QUrl(QStringLiteral("https://example.test/notify"))};
    n->setUrls(urls);
    report("urls list round-trip",
           n->urls() == urls);

    // 10) addAction + label round-trip.
    KNotificationAction *act = n->addAction(QStringLiteral("ok"));
    report("addAction returns a labeled action",
           act != nullptr && act->label() == QStringLiteral("ok"));

    // 11) addDefaultAction + defaultAction round-trip.
    KNotificationAction *defAct = n->addDefaultAction(QStringLiteral("open"));
    report("addDefaultAction sets the default action",
           defAct != nullptr && n->defaultAction() == defAct
               && defAct->label() == QStringLiteral("open"));

    // 12) autoDelete round-trip.
    n->setAutoDelete(true);
    const bool onOk = n->isAutoDelete();
    n->setAutoDelete(false);
    report("autoDelete set/get round-trip (true, false)",
           onOk && !n->isAutoDelete());

    delete n;
    std::printf("TEST SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
