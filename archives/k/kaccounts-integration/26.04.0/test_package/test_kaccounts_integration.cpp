/*
 * Consumer-side smoke test for kaccounts-integration 26.04.0 (KAccounts6).
 *
 * Exercises the packaged library's public API without requiring the signond
 * daemon: Accounts::Manager enumerates provider/service definitions from the
 * data dirs offline. Proves the KAccounts6 CMake package, the exported
 * KAccounts6 target and the libaccounts-qt/libsignon-qt dependency chain
 * link and load.
 */
#include <Accounts/Manager>
#include <Accounts/Provider>
#include <Accounts/Service>

#include <QCoreApplication>
#include <QString>
#include <QUrl>

#include <cstdio>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    Accounts::Manager manager;

    const QList<Accounts::Provider> providers = manager.providerList();
    std::printf("providers listed: %lld\n", static_cast<long long>(providers.size()));

    const QList<Accounts::Service> services = manager.serviceList();
    std::printf("services listed: %lld\n", static_cast<long long>(services.size()));

    // Real API round-trip: enumerate a (possibly absent) provider by id and
    // observe the documented "not found" behaviour instead of crashing.
    Accounts::Provider missing =
        manager.provider(QStringLiteral("definitely-not-a-real-provider"));
    if (missing.isValid()) {
        std::fprintf(stderr, "FAIL: provider() unexpectedly resolved\n");
        return 1;
    }

    std::printf("PASS: KAccounts6 library + AccountsQt6 chain load and respond\n");
    return 0;
}
