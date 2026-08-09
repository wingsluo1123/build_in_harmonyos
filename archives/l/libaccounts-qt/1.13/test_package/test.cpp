#include <Accounts/Manager>
#include <Accounts/Account>
#include <QCoreApplication>
#include <QDebug>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);

    // Test: create a Manager (uses libaccounts-glib internally)
    Accounts::Manager manager;

    // Test: list accounts (calls into libaccounts-glib)
    Accounts::AccountIdList accountList = manager.accountList();
    qDebug() << "Account count:" << accountList.count();

    // Test: list services
    Accounts::ServiceList serviceList = manager.serviceList();
    qDebug() << "Service count:" << serviceList.count();

    qDebug() << "libaccounts-qt test: OK";
    return 0;
}
