// Consumer test for karchive5 5.116.0.1 (KF5 :: KArchive).
//
// Exercises the installed library through its public API:
//   1. KTar write + read round trip;
//   2. KZip write + read round trip with DeflateCompression (zlib);
//   3. KCompressionDevice GZip write + read round trip (zlib deflate/inflate).
//
// Case 3 is the runtime proof that the non-PIC zlib/1.3.1 libz.a was linked
// into the shared KF5Archive correctly (-Wl,--exclude-libs,ALL, see the main
// recipe): without the flag the link fails; with a broken link the gzip
// round trip would fail or crash here.

#include <QByteArray>
#include <QFile>
#include <QTemporaryDir>

#include <KArchiveDirectory>
#include <KArchiveFile>
#include <KCompressionDevice>
#include <KTar>
#include <KZip>

#include <cstdio>

static int failures = 0;

static void check(bool ok, const char *label)
{
    std::printf("%s: %s\n", ok ? "PASS" : "FAIL", label);
    if (!ok) {
        ++failures;
    }
}

int main()
{
    QTemporaryDir dir;
    if (!dir.isValid()) {
        std::printf("FAIL: cannot create a temporary directory\n");
        return 1;
    }

    const QByteArray payload("KStars on HarmonyOS PC: KArchive link/runtime verification\n");

    // 1) KTar write + read round trip.
    const QString tarPath = dir.filePath(QStringLiteral("kstars.tar"));
    {
        KTar tar(tarPath, QStringLiteral("application/x-tar"));
        check(tar.open(QIODevice::WriteOnly), "tar open for writing");
        check(tar.writeFile(QStringLiteral("hello.txt"), payload), "tar writeFile");
        check(tar.close(), "tar close after write");
    }
    check(QFile::exists(tarPath), "tar file created");
    {
        KTar tar(tarPath, QStringLiteral("application/x-tar"));
        check(tar.open(QIODevice::ReadOnly), "tar open for reading");
        const KArchiveDirectory *root = tar.directory();
        const KArchiveFile *entry = root ? root->file(QStringLiteral("hello.txt")) : nullptr;
        check(entry != nullptr, "tar entry present");
        if (entry) {
            check(entry->data() == payload, "tar payload matches");
        }
        tar.close();
    }

    // 2) KZip write + read round trip (deflate goes through zlib).
    const QString zipPath = dir.filePath(QStringLiteral("kstars.zip"));
    {
        KZip zip(zipPath);
        check(zip.open(QIODevice::WriteOnly), "zip open for writing");
        zip.setCompression(KZip::DeflateCompression);
        check(zip.writeFile(QStringLiteral("hello.txt"), payload), "zip writeFile");
        check(zip.close(), "zip close after write");
    }
    {
        KZip zip(zipPath);
        check(zip.open(QIODevice::ReadOnly), "zip open for reading");
        const KArchiveDirectory *root = zip.directory();
        const KArchiveFile *entry = root ? root->file(QStringLiteral("hello.txt")) : nullptr;
        check(entry != nullptr, "zip entry present");
        if (entry) {
            check(entry->data() == payload, "zip payload matches");
        }
        zip.close();
    }

    // 3) KCompressionDevice GZip write + read round trip.
    const QString gzPath = dir.filePath(QStringLiteral("payload.gz"));
    {
        KCompressionDevice dev(gzPath, KCompressionDevice::GZip);
        check(dev.compressionType() == KCompressionDevice::GZip, "gzip filter available");
        check(dev.open(QIODevice::WriteOnly), "gzip open for writing");
        check(dev.write(payload) == payload.size(), "gzip write payload");
        dev.close();
    }
    {
        QFile raw(gzPath);
        check(raw.open(QIODevice::ReadOnly), "gzip raw open");
        const QByteArray head = raw.read(2);
        check(head.size() == 2
                  && static_cast<unsigned char>(head.at(0)) == 0x1f
                  && static_cast<unsigned char>(head.at(1)) == 0x8b,
              "gzip magic bytes 1f 8b");
        raw.close();
    }
    {
        KCompressionDevice dev(gzPath, KCompressionDevice::GZip);
        check(dev.open(QIODevice::ReadOnly), "gzip open for reading");
        check(dev.readAll() == payload, "gzip payload matches");
        dev.close();
    }

    std::printf("TEST SUMMARY: %d failure(s)\n", failures);
    return failures == 0 ? 0 : 1;
}
