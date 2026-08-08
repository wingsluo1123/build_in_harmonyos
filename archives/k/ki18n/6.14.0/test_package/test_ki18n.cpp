// test_ki18n.cpp — Verify KF6I18n library links correctly
#include <KLocalizedString>
#include <cstdio>

int main() {
    // KI18n provides i18n() and related functions
    // Simply verify the library links and the API is callable
    QString result = i18n("test_message");
    printf("ki18n test: KF6I18n linked and i18n() functional\n");
    printf("result: %s\n", result.toUtf8().data());
    return 0;
}
