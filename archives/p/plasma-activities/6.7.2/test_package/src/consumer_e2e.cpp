/*
    Consumer end-to-end cases for plasma-activities on HarmonyOS PC.

    SPDX-FileCopyrightText: 2026 OpenHarmonyPCDeveloper
    SPDX-License-Identifier: LGPL-2.1-or-later

    The runner drives the offline consumer contract that Plasma applications
    see on a system without kactivitymanagerd and without a session D-Bus:
    every case is judged independently (TEST PASS / TEST FAIL), the run ends
    with TEST SUMMARY and any failure makes the process exit non-zero.
*/

#include <QCoreApplication>
#include <QFuture>
#include <QStringList>
#include <QTextStream>

#include <functional>

#include <PlasmaActivities/Consumer>
#include <PlasmaActivities/Controller>
#include <PlasmaActivities/Info>
#include <PlasmaActivities/Version>

namespace
{
const QString kNullUuid = QStringLiteral("00000000-0000-0000-0000-000000000000");

QTextStream out(stdout);
int g_passed = 0;
int g_failed = 0;

void runCase(const QString &name, const std::function<bool(QString &)> &body)
{
    out << "RUN CASE: " << name << "\n";
    out.flush();

    QString reason;
    const bool ok = body(reason);
    if (ok) {
        ++g_passed;
        out << "TEST PASS: " << name << "\n";
    } else {
        ++g_failed;
        out << "TEST FAIL: " << name << ": " << reason << "\n";
    }
    out.flush();
}

#define REQUIRE(condition, message)                                            \
    do {                                                                       \
        if (!(condition)) {                                                    \
            reason = QStringLiteral(message);                                  \
            return false;                                                      \
        }                                                                      \
    } while (false)

bool caseVersion(QString &reason)
{
    REQUIRE(KActivities::versionMajor() == 6, "versionMajor() != 6");
    REQUIRE(KActivities::versionMinor() == 7, "versionMinor() != 7");
    REQUIRE(KActivities::versionRelease() == 2, "versionRelease() != 2");
    REQUIRE(QString::fromLatin1(KActivities::versionString())
                == QStringLiteral("6.7.2"),
            "versionString() != 6.7.2");
    return true;
}

bool caseConsumerOfflineStatus(QString &reason)
{
    KActivities::Consumer consumer;
    REQUIRE(consumer.serviceStatus() == KActivities::Consumer::NotRunning,
            "serviceStatus() must be NotRunning without a session bus");
    return true;
}

bool caseConsumerOfflineDefaults(QString &reason)
{
    KActivities::Consumer consumer;

    const QStringList activities = consumer.activities();
    REQUIRE(activities.size() == 1,
            "activities() must expose exactly the null activity offline");
    REQUIRE(activities.first() == kNullUuid,
            "activities() first entry must be the null activity");
    REQUIRE(consumer.currentActivity() == kNullUuid,
            "currentActivity() must be the null activity offline");
    return true;
}

bool caseControllerOfflineFutures(QString &reason)
{
    KActivities::Controller controller;
    REQUIRE(controller.serviceStatus() == KActivities::Consumer::NotRunning,
            "Controller must report NotRunning without a session bus");

    QFuture<QString> added = controller.addActivity(QStringLiteral("e2e-probe"));
    REQUIRE(added.isFinished(), "addActivity() future must complete offline");
    REQUIRE(added.result().isEmpty(),
            "addActivity() must not return an id offline");

    QFuture<bool> switched = controller.setCurrentActivity(kNullUuid);
    REQUIRE(switched.isFinished(),
            "setCurrentActivity() future must complete offline");
    REQUIRE(switched.result() == false,
            "setCurrentActivity() must fail offline");

    QFuture<void> renamed =
        controller.setActivityName(kNullUuid, QStringLiteral("e2e-probe"));
    REQUIRE(renamed.isFinished(),
            "setActivityName() future must complete offline");
    return true;
}

bool caseControllerOfflineRemainingOps(QString &reason)
{
    KActivities::Controller controller;

    QFuture<void> description =
        controller.setActivityDescription(kNullUuid, QStringLiteral("e2e"));
    REQUIRE(description.isFinished(),
            "setActivityDescription() future must complete offline");

    QFuture<void> icon =
        controller.setActivityIcon(kNullUuid, QStringLiteral("e2e"));
    REQUIRE(icon.isFinished(),
            "setActivityIcon() future must complete offline");

    QFuture<void> removed = controller.removeActivity(kNullUuid);
    REQUIRE(removed.isFinished(),
            "removeActivity() future must complete offline");

    QFuture<void> previous = controller.previousActivity();
    REQUIRE(previous.isFinished(),
            "previousActivity() future must complete offline");

    QFuture<void> next = controller.nextActivity();
    REQUIRE(next.isFinished(), "nextActivity() future must complete offline");
    return true;
}

bool caseInfoUnknownActivity(QString &reason)
{
    const QString unknown =
        QStringLiteral("9f1c4a52-3b7e-4d0a-9c1e-5b2d8f6a7c30");
    KActivities::Info info(unknown);

    REQUIRE(info.id() == unknown,
            "Info must keep the id it was constructed with");
    REQUIRE(info.uri() == QStringLiteral("activities://") + unknown,
            "Info uri must be the activities:// URI of the unknown id");
    REQUIRE(info.availability() == KActivities::Info::Nothing,
            "an unknown id must have Nothing availability offline");
    REQUIRE(!info.isCurrent(),
            "an unknown id must not be the current activity offline");
    REQUIRE(info.name().isEmpty(), "an unknown id must have an empty name");
    return true;
}

bool caseInfoOfflineAvailability(QString &reason)
{
    KActivities::Info info(kNullUuid);
    REQUIRE(info.availability() == KActivities::Info::Nothing,
            "Info availability must be Nothing without a running manager");
    REQUIRE(info.name().isEmpty(), "Info name must be empty offline");
    REQUIRE(info.description().isEmpty(),
            "Info description must be empty offline");
    REQUIRE(info.icon().isEmpty(), "Info icon must be empty offline");
    REQUIRE(info.uri() == QStringLiteral("activities://") + kNullUuid,
            "Info uri must be the activities:// URI of the id");
    return true;
}

} // namespace

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    out << "plasma-activities consumer E2E (offline contract on OHOS)\n";

    runCase(QStringLiteral("version-contract"), caseVersion);
    runCase(QStringLiteral("consumer-offline-status"),
            caseConsumerOfflineStatus);
    runCase(QStringLiteral("consumer-offline-defaults"),
            caseConsumerOfflineDefaults);
    runCase(QStringLiteral("controller-offline-futures"),
            caseControllerOfflineFutures);
    runCase(QStringLiteral("controller-offline-remaining-ops"),
            caseControllerOfflineRemainingOps);
    runCase(QStringLiteral("info-unknown-activity-id"),
            caseInfoUnknownActivity);
    runCase(QStringLiteral("info-offline-availability"),
            caseInfoOfflineAvailability);

    out << "TEST SUMMARY: " << g_passed << " passed, " << g_failed
        << " failed\n";
    out.flush();

    return g_failed == 0 ? 0 : 1;
}
