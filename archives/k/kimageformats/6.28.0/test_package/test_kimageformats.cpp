// kimageformats 6.28.0 consumer test: drives the packaged QImageIOHandler
// plugins through Qt's plugin infrastructure on the target device.
//
// Executor structure: per-case TEST PASS / TEST FAIL lines, a final
// TEST SUMMARY and a non-zero exit code when any case fails.
//
// Cases: plugin advertisement, HDR/TGA/QOI/DDS decodes, EXR and JP2
// write-read roundtrips (option-gated), package layout.
#include <QCoreApplication>
#include <QColor>
#include <QDir>
#include <QFile>
#include <QImage>
#include <QImageReader>
#include <QImageWriter>
#include <QStringList>
#include <QTemporaryDir>
#include <QTextStream>
#include <cstring>

static QTextStream out(stdout);

static int g_casesPassed = 0;
static int g_casesFailed = 0;
static bool g_caseFailed = false;

static void beginCase(const char *name)
{
    g_caseFailed = false;
    out << "CASE: " << name << '\n';
    out.flush();
}

static void check(bool ok, const QString &what)
{
    out << (ok ? "  ok: " : "  FAILED: ") << what << '\n';
    out.flush();
    if (!ok) {
        g_caseFailed = true;
    }
}

static void endCase(const char *name)
{
    if (g_caseFailed) {
        ++g_casesFailed;
        out << "TEST FAIL: " << name << '\n';
    } else {
        ++g_casesPassed;
        out << "TEST PASS: " << name << '\n';
    }
    out.flush();
}

// --------------------------------------------------------------- fixtures

static bool writeFile(const QString &path, const QByteArray &bytes)
{
    QFile f(path);
    if (!f.open(QIODevice::WriteOnly)) {
        return false;
    }
    return f.write(bytes) == bytes.size();
}

static QByteArray minimalHdr()
{
    // 1x1 Radiance RGBE, flat (non-RLE) scanline. Mantissa 0x80 with
    // exponent 0x80 decodes to a middle-grey linear value.
    QByteArray b("#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 1 +X 1\n");
    b.append('\x80');
    b.append('\x80');
    b.append('\x80');
    b.append('\x80');
    return b;
}

static QByteArray minimalTga()
{
    // 2x2 uncompressed 24-bit TGA, default descriptor (bottom-left origin).
    // Intended image: top row red, green; bottom row blue, white.
    QByteArray b(18 + 12, '\0');
    b[2] = 0x02;             // uncompressed true-color image
    b[12] = 2;               // width 2 (little endian)
    b[14] = 2;               // height 2 (little endian)
    b[16] = 24;              // bits per pixel
    const unsigned char pixels[12] = {
        // stored first: bottom row (BGR): blue, white
        0xFF, 0x00, 0x00, 0xFF, 0xFF, 0xFF,
        // stored second: top row (BGR): red, green
        0x00, 0x00, 0xFF, 0x00, 0xFF, 0x00,
    };
    std::memcpy(b.data() + 18, pixels, sizeof(pixels));
    return b;
}

static QByteArray minimalQoi()
{
    // 2x2 QOI: header ("qoif", big-endian size, 4 channels, sRGB) followed by
    // one QOI_OP_RGBA per pixel (row-major) and the 8-byte end marker.
    QByteArray b("qoif");
    b.append('\0'); b.append('\0'); b.append('\0'); b.append('\x02'); // width
    b.append('\0'); b.append('\0'); b.append('\0'); b.append('\x02'); // height
    b.append('\x04'); // channels
    b.append('\x00'); // colorspace
    const unsigned char px[20] = {
        0xFF, 255, 0, 0, 255,         // red
        0xFF, 0, 255, 0, 255,         // green
        0xFF, 0, 0, 255, 255,         // blue
        0xFF, 255, 255, 255, 255,     // white
    };
    b.append(reinterpret_cast<const char *>(px), sizeof(px));
    for (int i = 0; i < 7; ++i) {
        b.append('\0');
    }
    b.append('\x01');
    return b;
}

static QByteArray minimalDdsDxt1()
{
    // 4x4 DDS in DXT1: 128-byte header + one block. A solid-colour block has
    // colour0 (RGB565 red) and all index bits zero. colour0 > colour1 keeps
    // the block in 4-colour mode.
    QByteArray b(128 + 8, '\0');
    auto put32 = [&b](int off, quint32 v) {
        b[off] = char(v & 0xFF);
        b[off + 1] = char((v >> 8) & 0xFF);
        b[off + 2] = char((v >> 16) & 0xFF);
        b[off + 3] = char((v >> 24) & 0xFF);
    };
    put32(0, 0x20534444);    // magic "DDS "
    put32(4, 124);           // dwSize
    put32(8, 0x00081007);    // CAPS | HEIGHT | WIDTH | PIXELFORMAT | LINEARSIZE
    put32(12, 4);            // dwHeight
    put32(16, 4);            // dwWidth
    put32(20, 8);            // dwPitchOrLinearSize
    put32(76, 32);           // ddspf.dwSize
    put32(80, 0x4);          // ddspf.dwFlags = DDPF_FOURCC
    b[84] = 'D'; b[85] = 'X'; b[86] = 'T'; b[87] = '1';
    put32(108, 0x1000);      // dwCaps = DDSCAPS_TEXTURE
    put32(128, 0xF800);      // DXT1 colour0 = RGB565 red
    put32(132, 0x00000000);  // DXT1 colour1 = black
    return b;
}

static bool colorNear(const QColor &c, int r, int g, int b, int tolerance)
{
    return qAbs(c.red() - r) <= tolerance
        && qAbs(c.green() - g) <= tolerance
        && qAbs(c.blue() - b) <= tolerance;
}

// -------------------------------------------------------------------- main

static const QString kPluginPath = QStringLiteral(KIF_PLUGIN_DIR);

static bool roundTrip(const QString &path, const char *format,
                      QImage *decoded, QString *error)
{
    QImage source(4, 4, QImage::Format_RGB32);
    source.fill(QColor(200, 30, 30));
    QImageWriter writer(path, format);
    if (!writer.write(source)) {
        *error = QStringLiteral("write failed: %1").arg(writer.errorString());
        return false;
    }
    QImageReader reader(path);
    *decoded = reader.read();
    if (decoded->isNull()) {
        *error = QStringLiteral("read back failed: %1")
                     .arg(reader.errorString());
        return false;
    }
    return true;
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    // The package's "plugins" directory; Qt appends the "imageformats"
    // subdirectory to every library path.
    QCoreApplication::addLibraryPath(kPluginPath);

    const bool expectDds = KIF_EXPECT_DDS != 0;
    const bool expectExr = KIF_EXPECT_OPENEXR != 0;
    const bool expectRaw = KIF_EXPECT_LIBRAW != 0;
    const bool expectJp2 = KIF_EXPECT_OPENJPEG != 0;
    const bool expectAvif = KIF_EXPECT_LIBAVIF != 0;

    QTemporaryDir tmp;
    if (!tmp.isValid()) {
        out << "FAIL: cannot create temporary directory\n";
        return 1;
    }

    // --- case 1: plugin advertisement -------------------------------------
    beginCase("plugin-advertisement");
    const QList<QByteArray> formats = QImageReader::supportedImageFormats();
    QStringList expected{"ani", "ff", "hdr", "iff", "pcx", "pic", "pfm",
                         "psd", "pxr", "qoi", "ras", "rgb", "sct", "tim",
                         "tga", "xcf"};
    if (expectDds) {
        expected << "dds";
    }
    if (expectExr) {
        expected << "exr";
    }
    if (expectRaw) {
        expected << "raw";
    }
    if (expectJp2) {
        expected << "jp2";
    }
    if (expectAvif) {
        expected << "avif";
    }
    QStringList missing;
    for (const QString &key : expected) {
        if (!formats.contains(key.toLatin1())) {
            missing << key;
        }
    }
    check(missing.isEmpty(),
          QStringLiteral("%1 expected format keys advertised (missing: %2)")
              .arg(expected.size())
              .arg(missing.isEmpty() ? QStringLiteral("none")
                                     : missing.join(QLatin1Char(','))));
    check(!formats.contains("heif") && !formats.contains("jxl")
              && !formats.contains("jxr"),
          QStringLiteral("disabled formats (heif/jxl/jxr) not advertised"));
    endCase("plugin-advertisement");

    // --- case 2: HDR decode ----------------------------------------------
    beginCase("hdr-decode");
    const QString hdrFile = tmp.filePath(QStringLiteral("sample.hdr"));
    check(writeFile(hdrFile, minimalHdr()),
          QStringLiteral("wrote 1x1 HDR fixture"));
    QImageReader hdrReader(hdrFile);
    const QImage hdr = hdrReader.read();
    check(!hdr.isNull(),
          QStringLiteral("HDR decode succeeded (%1)")
              .arg(hdrReader.errorString()));
    if (!hdr.isNull()) {
        check(hdr.width() == 1 && hdr.height() == 1,
              QStringLiteral("decoded size 1x1 (got %1x%2)")
                  .arg(hdr.width()).arg(hdr.height()));
        const QColor c = hdr.pixelColor(0, 0);
        check(c.red() == c.green() && c.green() == c.blue(),
              QStringLiteral("grey pixel (rgb %1,%2,%3)")
                  .arg(c.red()).arg(c.green()).arg(c.blue()));
        check(c.red() > 120 && c.red() < 240,
              QStringLiteral("mid-tone brightness (r=%1)").arg(c.red()));
    }
    endCase("hdr-decode");

    // --- case 3: TGA decode ----------------------------------------------
    beginCase("tga-decode");
    const QString tgaFile = tmp.filePath(QStringLiteral("sample.tga"));
    check(writeFile(tgaFile, minimalTga()),
          QStringLiteral("wrote 2x2 TGA fixture"));
    QImageReader tgaReader(tgaFile);
    const QImage tga = tgaReader.read();
    check(!tga.isNull(),
          QStringLiteral("TGA decode succeeded (%1)")
              .arg(tgaReader.errorString()));
    if (!tga.isNull()) {
        check(tga.width() == 2 && tga.height() == 2,
              QStringLiteral("decoded size 2x2 (got %1x%2)")
                  .arg(tga.width()).arg(tga.height()));
        check(tga.pixelColor(0, 0) == QColor(255, 0, 0),
              QStringLiteral("top-left red"));
        check(tga.pixelColor(1, 0) == QColor(0, 255, 0),
              QStringLiteral("top-right green"));
        check(tga.pixelColor(0, 1) == QColor(0, 0, 255),
              QStringLiteral("bottom-left blue"));
        check(tga.pixelColor(1, 1) == QColor(255, 255, 255),
              QStringLiteral("bottom-right white"));
    }
    endCase("tga-decode");

    // --- case 4: QOI decode ----------------------------------------------
    beginCase("qoi-decode");
    const QString qoiFile = tmp.filePath(QStringLiteral("sample.qoi"));
    check(writeFile(qoiFile, minimalQoi()),
          QStringLiteral("wrote 2x2 QOI fixture"));
    QImageReader qoiReader(qoiFile);
    const QImage qoi = qoiReader.read();
    check(!qoi.isNull(),
          QStringLiteral("QOI decode succeeded (%1)")
              .arg(qoiReader.errorString()));
    if (!qoi.isNull()) {
        check(qoi.width() == 2 && qoi.height() == 2,
              QStringLiteral("decoded size 2x2 (got %1x%2)")
                  .arg(qoi.width()).arg(qoi.height()));
        check(qoi.pixelColor(0, 0) == QColor(255, 0, 0),
              QStringLiteral("top-left red"));
        check(qoi.pixelColor(1, 0) == QColor(0, 255, 0),
              QStringLiteral("top-right green"));
        check(qoi.pixelColor(0, 1) == QColor(0, 0, 255),
              QStringLiteral("bottom-left blue"));
        check(qoi.pixelColor(1, 1) == QColor(255, 255, 255),
              QStringLiteral("bottom-right white"));
    }
    endCase("qoi-decode");

    // --- case 5: DDS (DXT1) decode ---------------------------------------
    beginCase("dds-decode");
    const QString ddsFile = tmp.filePath(QStringLiteral("sample.dds"));
    check(writeFile(ddsFile, minimalDdsDxt1()),
          QStringLiteral("wrote 4x4 DXT1 DDS fixture"));
    QImageReader ddsReader(ddsFile);
    const QImage dds = ddsReader.read();
    check(!dds.isNull(),
          QStringLiteral("DDS decode succeeded (%1)")
              .arg(ddsReader.errorString()));
    if (!dds.isNull()) {
        check(dds.width() == 4 && dds.height() == 4,
              QStringLiteral("decoded size 4x4 (got %1x%2)")
                  .arg(dds.width()).arg(dds.height()));
        check(colorNear(dds.pixelColor(2, 2), 255, 0, 0, 16),
              QStringLiteral("solid red block (rgb %1,%2,%3)")
                  .arg(dds.pixelColor(2, 2).red())
                  .arg(dds.pixelColor(2, 2).green())
                  .arg(dds.pixelColor(2, 2).blue()));
    }
    endCase("dds-decode");

    // --- case 6: EXR write-read roundtrip (option-gated) -----------------
    beginCase("exr-roundtrip");
    if (!expectExr) {
        out << "  skip: OpenEXR plugin not built in this package\n";
    } else {
        QImage decoded;
        QString error;
        check(roundTrip(tmp.filePath(QStringLiteral("roundtrip.exr")),
                        "exr", &decoded, &error),
              QStringLiteral("EXR write+read cycle (%1)")
                  .arg(error.isEmpty() ? QStringLiteral("ok") : error));
        if (!decoded.isNull()) {
            check(decoded.width() == 4 && decoded.height() == 4,
                  QStringLiteral("roundtripped size 4x4 (got %1x%2)")
                      .arg(decoded.width()).arg(decoded.height()));
            const QColor c = decoded.pixelColor(1, 1);
            check(c.red() > 140 && c.green() < 90 && c.blue() < 90,
                  QStringLiteral("roundtripped colour near input (rgb %1,%2,%3)")
                      .arg(c.red()).arg(c.green()).arg(c.blue()));
        }
    }
    endCase("exr-roundtrip");

    // --- case 7: JP2 write-read roundtrip (option-gated) -----------------
    beginCase("jp2-roundtrip");
    if (!expectJp2) {
        out << "  skip: OpenJPEG plugin not built in this package\n";
    } else {
        QImage decoded;
        QString error;
        check(roundTrip(tmp.filePath(QStringLiteral("roundtrip.jp2")),
                        "jp2", &decoded, &error),
              QStringLiteral("JP2 write+read cycle (%1)")
                  .arg(error.isEmpty() ? QStringLiteral("ok") : error));
        if (!decoded.isNull()) {
            check(decoded.width() == 4 && decoded.height() == 4,
                  QStringLiteral("roundtripped size 4x4 (got %1x%2)")
                      .arg(decoded.width()).arg(decoded.height()));
            const QColor c = decoded.pixelColor(1, 1);
            check(c.red() > 120 && c.green() < 110 && c.blue() < 110,
                  QStringLiteral("roundtripped colour near input (rgb %1,%2,%3)")
                      .arg(c.red()).arg(c.green()).arg(c.blue()));
        }
    }
    endCase("jp2-roundtrip");

    // --- case 8: package layout ------------------------------------------
    beginCase("package-layout");
    const QDir pluginDir(kPluginPath + QStringLiteral("/imageformats"));
    check(pluginDir.exists(),
          QStringLiteral("package ships plugins/imageformats"));
    const QStringList soFiles =
        pluginDir.entryList(QStringList{QStringLiteral("kimg_*.so")},
                            QDir::Files);
    check(soFiles.size() == 21,
          QStringLiteral("21 kimg_*.so plugins (%1 found)")
              .arg(soFiles.size()));
    const QStringList outOfScope{"kimg_heif", "kimg_jxl", "kimg_jxr",
                                 "kimg_kra", "kimg_ora", "kimg_eps"};
    for (const QString &name : outOfScope) {
        check(!pluginDir.exists(name + QStringLiteral(".so")),
              QStringLiteral("%1.so absent (scope decision)").arg(name));
    }
    endCase("package-layout");

    out << "TEST SUMMARY: " << g_casesPassed << " passed, " << g_casesFailed
        << " failed\n";
    out.flush();
    return g_casesFailed == 0 ? 0 : 1;
}
