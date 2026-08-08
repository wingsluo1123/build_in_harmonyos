// test_kcoreaddons.cpp — Verify KF6CoreAddons library links correctly
#include <KAboutData>
#include <KProcess>
#include <cstdio>

int main() {
    KAboutData about("test_app", "Test App", "1.0");
    KProcess process;
    printf("kcoreaddons test: KF6CoreAddons linked and functional\n");
    printf("aboutData shortName: %s\n", about.componentName().toUtf8().constData());
    return 0;
}
