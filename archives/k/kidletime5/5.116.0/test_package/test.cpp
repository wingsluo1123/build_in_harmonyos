// kidletime5 5.116.0 consumer test (R34: exercises real API).
// Instantiates the KIdleTime singleton and queries the current idle time.
#include <KIdleTime>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    KIdleTime *idle = KIdleTime::instance();
    if (!idle) {
        std::printf("FAIL: KIdleTime::instance() returned null\n");
        return 1;
    }
    std::printf("PASS: KIdleTime linked and instance available; idleTime=%d ms\n",
                idle->idleTime());
    return 0;
}
