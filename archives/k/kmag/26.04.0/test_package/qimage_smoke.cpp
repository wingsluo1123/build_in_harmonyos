// SPDX-License-Identifier: GPL-2.0-or-later
//
// Consumer E2E for kmag 26.04.0: reproduces the snapshot export path of
// saveZoomPixmap() — render a QImage with QPainter, write it through
// QImageWriter as PNG into a temporary file, read it back with
// QImageReader and verify size and pixel content. This is the Qt-side
// half of the application's save flow (the file is afterwards handed to
// KIO::file_copy by the application).
//
// The executor prints one TEST PASS / TEST FAIL line per case and a
// TEST SUMMARY line; any failure makes the process exit 1.

#include <QCoreApplication>
#include <QFileInfo>
#include <QImage>
#include <QImageReader>
#include <QImageWriter>
#include <QPainter>
#include <QTemporaryDir>

#include <cstdio>

static int g_passed = 0;
static int g_failed = 0;

static void check(bool ok, const char *name)
{
    if (ok) {
        std::printf("TEST PASS: %s\n", name);
        ++g_passed;
    } else {
        std::printf("TEST FAIL: %s\n", name);
        ++g_failed;
    }
}

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    QTemporaryDir tmpDir;
    check(tmpDir.isValid(), "temporary export directory is created");

    QImage image(128, 96, QImage::Format_ARGB32_Premultiplied);
    image.fill(Qt::transparent);
    {
        QPainter painter(&image);
        painter.fillRect(8, 8, 64, 48, QColor(200, 30, 30));
        painter.fillRect(80, 56, 32, 24, QColor(30, 30, 200));
        painter.end();
    }

    const QString path = tmpDir.filePath(QStringLiteral("kmag-snapshot.png"));

    QImageWriter writer(path, "png");
    check(writer.canWrite(), "PNG image writer is available");
    check(writer.write(image), "magnified view is written to a PNG file");
    check(QFileInfo::exists(path) && QFileInfo(path).size() > 0,
          "exported snapshot file exists and is non-empty");

    QImageReader reader(path);
    const QImage restored = reader.read();
    check(!restored.isNull(), "exported snapshot can be read back");
    check(restored.size() == image.size(), "restored size matches the source");
    check(restored.pixelColor(16, 16) == QColor(200, 30, 30),
          "restored pixel matches the rendered view");

    std::printf("TEST SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
