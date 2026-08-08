// test_kconfig.cpp — Verify KF6ConfigCore library links correctly
#include <KConfig>
#include <KConfigGroup>
#include <cstdio>

int main() {
    KConfig config("test_config");
    KConfigGroup group(&config, "TestGroup");
    group.writeEntry("test_key", QString("test_value"));
    config.sync();
    printf("kconfig test: KF6ConfigCore linked and functional\n");
    return 0;
}
