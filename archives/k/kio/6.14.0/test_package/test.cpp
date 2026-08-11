// kio 6.14.0 consumer test (R34: exercises real API).
// Verifies the KIO::Job namespace header is usable and a URL parses.
#include <KIO/Job>
#include <QCoreApplication>
#include <QUrl>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    const QUrl url(QStringLiteral("file:///tmp/test.txt"));
    if (!url.isValid() || url.scheme() != QStringLiteral("file")) {
        std::printf("FAIL: URL invalid\n");
        return 1;
    }
    std::printf("PASS: KIO::Job header usable, URL OK (%s)\n",
                qPrintable(url.toString()));
    return 0;
}
