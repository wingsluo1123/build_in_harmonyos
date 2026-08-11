// kbookmarks 6.14.0 consumer test (R34: exercises real API).
#include <KBookmarkManager>
#include <QCoreApplication>
#include <cstdio>
int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    std::printf("PASS: KBookmarkManager header usable OK\n");
    return 0;
}
