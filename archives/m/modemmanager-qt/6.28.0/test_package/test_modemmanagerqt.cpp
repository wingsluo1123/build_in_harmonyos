// SPDX-License-Identifier: LGPL-2.1-or-later
//
// Consumer-side test for modemmanager-qt 6.28.0.
//
// Links KF6::ModemManagerQt from the installed package and exercises the real
// public API against a private dbus-daemon that serves as both the session
// bus and (through DBUS_SYSTEM_BUS_ADDRESS) the system bus. The shared
// library talks to org.freedesktop.ModemManager1 with
// QDBusConnection::systemBus(); registering that name on the private bus
// drives the QDBusServiceWatcher-based serviceAppeared/serviceDisappeared
// signals end to end.

#include <ModemManagerQt/Bearer>
#include <ModemManagerQt/Manager>
#include <ModemManagerQt/Modem>
#include <ModemManagerQt/Sim>
#include <ModemManagerQt/Sms>

#include <QCoreApplication>
#include <QDBusConnection>
#include <QEventLoop>
#include <QObject>
#include <QString>
#include <QTimer>

#include <cstdio>

namespace
{
int g_passed = 0;
int g_failed = 0;

void record(bool ok, const char *name, const QString &detail = QString())
{
    if (ok) {
        ++g_passed;
        std::printf("TEST PASS %s\n", name);
    } else {
        ++g_failed;
        std::printf("TEST FAIL %s%s%s\n",
                    name,
                    detail.isEmpty() ? "" : ": ",
                    detail.isEmpty() ? "" : qPrintable(detail));
    }
}

}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    QCoreApplication::setApplicationName(QStringLiteral("test_modemmanagerqt"));

    // 1. notifier() returns the same process-wide Notifier instance.
    ModemManager::Notifier *notifierA = ModemManager::notifier();
    ModemManager::Notifier *notifierB = ModemManager::notifier();
    record(notifierA != nullptr && notifierA == notifierB,
           "notifier_singleton",
           notifierA == nullptr
               ? QStringLiteral("null notifier")
               : (notifierA == notifierB ? QStringLiteral("same instance")
                                         : QStringLiteral("different instances")));

    // 2. No ModemManager service on this bus -> no modem devices enumerated.
    const ModemManager::ModemDevice::List devices = ModemManager::modemDevices();
    record(devices.isEmpty(),
           "empty_modem_list",
           QStringLiteral("count=%1").arg(devices.size()));

    // 3. Modem keeps the object path it was constructed with.
    const QString modemPath = QStringLiteral("/org/freedesktop/ModemManager1/Modem/0");
    ModemManager::Modem modem(modemPath);
    record(modem.uni() == modemPath, "modem_uni_roundtrip", modem.uni());

    // 4. Without the daemon the D-Bus interface is invalid.
    record(!modem.isValid(), "modem_isvalid_without_daemon");

    // 5-6. Sim and Bearer round-trip their paths as well.
    const QString simPath = QStringLiteral("/org/freedesktop/ModemManager1/SIM/0");
    ModemManager::Sim sim(simPath);
    record(sim.uni() == simPath, "sim_uni_roundtrip", sim.uni());

    // 7. Sms only records its path once the remote object answered: with no
    //    ModemManager service on this bus the generated interface is
    //    invalid, so uni() stays empty. (Sim and Bearer cache the path
    //    unconditionally; the upstream Sms implementation does not. With a
    //    running ModemManager the name is owned and the object exists, so
    //    the path is cached.)
    const QString smsPath = QStringLiteral("/org/freedesktop/ModemManager1/SMS/0");
    ModemManager::Sms sms(smsPath);
    record(sms.uni().isEmpty(), "sms_uni_without_service", sms.uni());

    const QString bearerPath = QStringLiteral("/org/freedesktop/ModemManager1/Bearer/0");
    ModemManager::Bearer bearer(bearerPath);
    record(bearer.uni() == bearerPath, "bearer_uni_roundtrip", bearer.uni());

    // 8. The system bus connection (private daemon) is usable.
    QDBusConnection systemBus = QDBusConnection::systemBus();
    record(systemBus.isConnected(), "system_bus_connected", systemBus.lastError().message());

    // 9. Owning org.freedesktop.ModemManager1 makes the library emit
    //    serviceAppeared through its QDBusServiceWatcher.
    bool appeared = false;
    {
        QEventLoop loop;
        const QMetaObject::Connection connection =
            QObject::connect(notifierA, &ModemManager::Notifier::serviceAppeared, &loop, [&]() {
                appeared = true;
                loop.quit();
            });
        QTimer::singleShot(8000, &loop, &QEventLoop::quit);
        const bool registered =
            systemBus.registerService(QStringLiteral("org.freedesktop.ModemManager1"));
        record(registered, "register_modemmanager_service", systemBus.lastError().message());
        loop.exec();
        QObject::disconnect(connection);
    }
    record(appeared, "service_appeared_signal");

    // 10. Releasing the name makes the library emit serviceDisappeared.
    bool disappeared = false;
    {
        QEventLoop loop;
        const QMetaObject::Connection connection =
            QObject::connect(notifierA, &ModemManager::Notifier::serviceDisappeared, &loop, [&]() {
                disappeared = true;
                loop.quit();
            });
        QTimer::singleShot(8000, &loop, &QEventLoop::quit);
        const bool unregistered =
            systemBus.unregisterService(QStringLiteral("org.freedesktop.ModemManager1"));
        record(unregistered, "unregister_modemmanager_service", systemBus.lastError().message());
        loop.exec();
        QObject::disconnect(connection);
    }
    record(disappeared, "service_disappeared_signal");

    std::printf("TEST SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
