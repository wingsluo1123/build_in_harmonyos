// kio 6.14.0 consumer test (R34: exercises real API).
// Calls KIO::stat() on a file URL and verifies the returned StatJob can be
// started and awaited via KJob::exec(), proving the KIO library links and
// its runtime API is callable.
#include <KIO/StatJob>
#include <KJob>
#include <QCoreApplication>
#include <QUrl>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    // A definitely-missing path is fine: KIO::stat must return a StatJob
    // object and exec() must complete (with error) without crashing.
    const QUrl url(QStringLiteral("file:///nonexistent/kio-test"));
    KIO::StatJob *job = KIO::stat(url, KIO::DefaultFlags);
    if (!job) {
        std::printf("FAIL: KIO::stat returned null\n");
        return 1;
    }
    job->exec();
    std::printf("PASS: KIO::stat created and executed OK (error=%d)\n",
                job->error());
    return 0;
}
