#include <KGAPI/Account>
#include <KGAPI/AccountManager>
#include <KGAPI/Calendar/Event>

#include <QCoreApplication>
#include <QDebug>
#include <QUrl>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    KGAPI2::Account account(QStringLiteral("ada@example.test"),
                            QStringLiteral("access-token"),
                            QStringLiteral("refresh-token"),
                            {KGAPI2::Account::mailScopeUrl()});
    if (account.accountName() != QLatin1StringView("ada@example.test")) {
        qCritical() << "Unexpected account name" << account.accountName();
        return 1;
    }
    if (!account.scopes().contains(KGAPI2::Account::mailScopeUrl())) {
        qCritical() << "Missing mail scope" << account.scopes();
        return 1;
    }

    if (!KGAPI2::AccountManager::instance()) {
        qCritical() << "AccountManager singleton is null";
        return 1;
    }

    KGAPI2::Event event;
    event.setId(QStringLiteral("event-id"));
    event.setSummary(QStringLiteral("OHOS libkgapi smoke"));
    if (event.id() != QLatin1StringView("event-id")) {
        qCritical() << "Unexpected event id" << event.id();
        return 1;
    }

    qDebug().noquote() << "PASS: KPim6GAPI account scope" << account.accountName();
    qDebug().noquote() << "PASS: KPim6GAPI calendar event" << event.summary();
    return 0;
}
