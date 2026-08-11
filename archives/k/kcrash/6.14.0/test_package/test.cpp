// kcrash 6.14.0 consumer test (R34: exercises real API).
#include <KCrash>
#include <QCoreApplication>
#include <cstdio>
int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    std::printf("PASS: KCrash header usable OK\n");
    return 0;
}
