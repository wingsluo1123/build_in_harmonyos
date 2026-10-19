// karchive 6.28.0 consumer test (R34: exercises the installed package API).
// Runs four end-to-end round-trips through the packaged KF6Archive library:
// KTar (gzip tar), KZip (zip) and KCompressionDevice with the GZip and Xz
// filters. Each case prints its own TEST PASS / TEST FAIL line, the run ends
// with TEST SUMMARY, and any failed case makes the process exit non-zero.
#include <KArchiveDirectory>
#include <KArchiveFile>
#include <KCompressionDevice>
#include <KTar>
#include <KZip>
#include <QByteArray>
#include <QCoreApplication>
#include <QFileInfo>
#include <QIODevice>
#include <QTemporaryDir>
#include <cstdio>

static int s_passed = 0;
static int s_failed = 0;

static void reportPass(const char *name)
{
    ++s_passed;
    std::printf("TEST PASS: %s\n", name);
    std::fflush(stdout);
}

static void reportFail(const char *name, const char *why)
{
    ++s_failed;
    std::printf("TEST FAIL: %s (%s)\n", name, why);
    std::fflush(stdout);
}

static const char kPayloadText[] = "hello from karchive\n";

static void testKtarGzipRoundtrip(const QTemporaryDir &dir)
{
    static const char *name = "ktar-gzip-write-read";
    const QString archivePath = dir.filePath(QStringLiteral("payload.tar.gz"));
    const QByteArray payload(kPayloadText);

    {
        KTar tar(archivePath, QStringLiteral("application/gzip"));
        if (!tar.open(QIODevice::WriteOnly)) {
            return reportFail(name, "could not open gzip tar for writing");
        }
        if (!tar.writeFile(QStringLiteral("docs/payload.txt"), payload)) {
            return reportFail(name, "could not write file into archive");
        }
        if (!tar.close() || !QFileInfo::exists(archivePath)) {
            return reportFail(name, "archive close/save failed");
        }
    }

    KTar tar(archivePath, QStringLiteral("application/gzip"));
    if (!tar.open(QIODevice::ReadOnly)) {
        return reportFail(name, "could not open gzip tar for reading");
    }
    const KArchiveDirectory *root = tar.directory();
    if (root == nullptr) {
        return reportFail(name, "archive root directory is null");
    }
    const KArchiveFile *file = root->file(QStringLiteral("docs/payload.txt"));
    if (file == nullptr) {
        return reportFail(name, "payload file missing from archive");
    }
    if (file->data() != payload) {
        return reportFail(name, "payload did not round-trip");
    }
    if (!tar.close()) {
        return reportFail(name, "close after read failed");
    }
    reportPass(name);
}

static void testKzipZipRoundtrip(const QTemporaryDir &dir)
{
    static const char *name = "kzip-zip-write-read";
    const QString archivePath = dir.filePath(QStringLiteral("payload.zip"));
    const QByteArray payload(kPayloadText);

    {
        KZip zip(archivePath);
        if (!zip.open(QIODevice::WriteOnly)) {
            return reportFail(name, "could not open zip for writing");
        }
        if (!zip.writeFile(QStringLiteral("docs/payload.txt"), payload)) {
            return reportFail(name, "could not write file into zip");
        }
        if (!zip.close() || !QFileInfo::exists(archivePath)) {
            return reportFail(name, "zip close/save failed");
        }
    }

    KZip zip(archivePath);
    if (!zip.open(QIODevice::ReadOnly)) {
        return reportFail(name, "could not open zip for reading");
    }
    const KArchiveDirectory *root = zip.directory();
    if (root == nullptr) {
        return reportFail(name, "archive root directory is null");
    }
    const KArchiveFile *file = root->file(QStringLiteral("docs/payload.txt"));
    if (file == nullptr) {
        return reportFail(name, "payload file missing from zip");
    }
    if (file->data() != payload) {
        return reportFail(name, "payload did not round-trip");
    }
    if (!zip.close()) {
        return reportFail(name, "close after read failed");
    }
    reportPass(name);
}

static void testCompressionDeviceRoundtrip(const QTemporaryDir &dir,
                                           const char *name,
                                           const QString &fileName,
                                           KCompressionDevice::CompressionType type)
{
    const QString filePath = dir.filePath(fileName);
    const QByteArray payload(kPayloadText);

    {
        KCompressionDevice dev(filePath, type);
        if (!dev.open(QIODevice::WriteOnly)) {
            return reportFail(name, "could not open compression device for writing");
        }
        if (dev.write(payload) != payload.size()) {
            return reportFail(name, "short write through compression device");
        }
        dev.close();
        if (!QFileInfo::exists(filePath)) {
            return reportFail(name, "compressed file was not created");
        }
    }

    KCompressionDevice dev(filePath, type);
    if (!dev.open(QIODevice::ReadOnly)) {
        return reportFail(name, "could not open compression device for reading");
    }
    const QByteArray out = dev.readAll();
    dev.close();
    if (out != payload) {
        return reportFail(name, "payload did not round-trip");
    }
    reportPass(name);
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    QTemporaryDir dir;
    if (!dir.isValid()) {
        reportFail("environment", "could not create temporary directory");
        std::printf("TEST SUMMARY: %d passed, %d failed\n", s_passed, s_failed);
        return 1;
    }

    testKtarGzipRoundtrip(dir);
    testKzipZipRoundtrip(dir);
    testCompressionDeviceRoundtrip(dir, "kgzipfilter-compression-device",
                                   QStringLiteral("payload.gz"),
                                   KCompressionDevice::GZip);
    testCompressionDeviceRoundtrip(dir, "kxzfilter-compression-device",
                                   QStringLiteral("payload.xz"),
                                   KCompressionDevice::Xz);

    std::printf("TEST SUMMARY: %d passed, %d failed\n", s_passed, s_failed);
    return s_failed == 0 ? 0 : 1;
}
