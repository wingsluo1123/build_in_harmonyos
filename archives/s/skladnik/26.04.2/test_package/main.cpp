// Consumer test for skladnik 26.04.2 (application package, upstream N=0).
//
// Three groups of checks, all against the *installed package*:
//   A. the delivered ELF artifact (structure the OHOS loader requires)
//   B. the delivered executable actually running (offscreen QApplication)
//   C. the installed theme data contract KGameRenderer consumes at runtime
//
// Counting scheme (declared in MANIFEST.yml and in the PR tables): one
// numbered check = one independently judgeable assertion. Every check
// prints exactly one [PASS]/[FAIL]/[SKIP] line; the exit code is non-zero
// if any check fails.

#include <QByteArray>
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QProcess>
#include <QProcessEnvironment>
#include <QRegularExpression>
#include <QString>
#include <QStringList>

#include <cstdio>
#include <cstring>

namespace {

int g_index = 0;
int g_passed = 0;
int g_failed = 0;
int g_skipped = 0;

void report(const char *verdict, const QString &name, const QString &detail)
{
    ++g_index;
    std::printf("[%s] %02d %s%s%s\n", verdict, g_index,
                qPrintable(name), detail.isEmpty() ? "" : " - ",
                qPrintable(detail));
    std::fflush(stdout);
}

void pass(const QString &name, const QString &detail = QString())
{
    ++g_passed;
    report("PASS", name, detail);
}

void fail(const QString &name, const QString &detail)
{
    ++g_failed;
    report("FAIL", name, detail);
}

void skip(const QString &name, const QString &reason)
{
    ++g_skipped;
    report("SKIP", name, reason);
}

// ---------------------------------------------------------------------
// Minimal ELF64 reader (no readelf/llvm-readobj dependency on the worker).
// ---------------------------------------------------------------------

struct Elf64 {
    QByteArray data;
    bool valid = false;
    quint16 machine = 0;
    quint64 phoff = 0;
    quint16 phentsize = 0;
    quint16 phnum = 0;
    quint64 shoff = 0;
    quint16 shentsize = 0;
    quint16 shnum = 0;
    quint16 shstrndx = 0;

    static Elf64 load(const QString &path)
    {
        Elf64 e;
        QFile f(path);
        if (!f.open(QIODevice::ReadOnly)) {
            return e;
        }
        e.data = f.readAll();
        f.close();
        if (e.data.size() < 64) {
            return e;
        }
        const uchar *d = reinterpret_cast<const uchar *>(e.data.constData());
        if (std::memcmp(d, "\x7f" "ELF", 4) != 0) {
            return e;
        }
        if (d[4] != 2 || d[5] != 1) {  // ELFCLASS64 + little endian only
            return e;
        }
        auto rd16 = [&](int off) { return quint16(d[off] | (d[off + 1] << 8)); };
        auto rd32 = [&](int off) {
            return quint32(d[off] | (d[off + 1] << 8) | (d[off + 2] << 16)
                           | (quint32(d[off + 3]) << 24));
        };
        auto rd64 = [&](int off) {
            return quint64(rd32(off)) | (quint64(rd32(off + 4)) << 32);
        };
        e.machine = rd16(18);
        e.phoff = rd64(0x20);
        e.shoff = rd64(0x28);
        e.phentsize = rd16(0x36);
        e.phnum = rd16(0x38);
        e.shentsize = rd16(0x3A);
        e.shnum = rd16(0x3C);
        e.shstrndx = rd16(0x3E);
        e.valid = true;
        return e;
    }

    quint64 phField(int i, int off) const
    {
        const quint64 p = phoff + quint64(i) * phentsize;
        if (p + quint64(off) + 8 > quint64(data.size())) {
            return 0;
        }
        const quint64 q = p + quint64(off);
        const uchar *d = reinterpret_cast<const uchar *>(data.constData());
        auto rd32 = [&](quint64 o) {
            return quint32(d[o]) | (quint32(d[o + 1]) << 8)
                | (quint32(d[o + 2]) << 16) | (quint32(d[o + 3]) << 24);
        };
        return quint64(rd32(q)) | (quint64(rd32(q + 4)) << 32);
    }

    quint32 phType(int i) const
    {
        const quint64 p = phoff + quint64(i) * phentsize;
        if (p + 4 > quint64(data.size())) {
            return 0;
        }
        const uchar *d = reinterpret_cast<const uchar *>(data.constData());
        return quint32(d[p] | (d[p + 1] << 8) | (d[p + 2] << 16)
                       | (quint32(d[p + 3]) << 24));
    }

    // Section headers: name offset, type, offset, size.
    struct Section {
        quint32 nameOff = 0;
        quint32 type = 0;
        quint64 offset = 0;
        quint64 size = 0;
    };

    Section section(int i) const
    {
        Section s;
        const quint64 p = shoff + quint64(i) * shentsize;
        if (p + 64 > quint64(data.size())) {
            return s;
        }
        const uchar *d = reinterpret_cast<const uchar *>(data.constData());
        auto rd32 = [&](quint64 off) {
            return quint32(d[off] | (d[off + 1] << 8) | (d[off + 2] << 16)
                           | (quint32(d[off + 3]) << 24));
        };
        auto rd64 = [&](quint64 off) {
            return quint64(rd32(off)) | (quint64(rd32(off + 4)) << 32);
        };
        s.nameOff = rd32(p);
        s.type = rd32(p + 4);
        s.offset = rd64(p + 0x18);
        s.size = rd64(p + 0x20);
        return s;
    }

    QString sectionName(const Section &s) const
    {
        if (shstrndx >= shnum) {
            return QString();
        }
        const Section strtab = section(shstrndx);
        const quint64 start = strtab.offset + s.nameOff;
        if (start >= quint64(data.size())) {
            return QString();
        }
        const char *base = data.constData() + start;
        const qint64 max = data.size() - qint64(start);
        return QString::fromLatin1(base, int(qstrnlen(base, max)));
    }

    QStringList needed() const
    {
        QStringList out;
        for (int i = 0; i < shnum; ++i) {
            const Section s = section(i);
            if (s.type != 6) {  // SHT_DYNAMIC
                continue;
            }
            const Section strtab = dynstr();
            if (strtab.offset == 0 && strtab.size == 0) {
                continue;
            }
            for (quint64 p = s.offset; p + 16 <= s.offset + s.size
                 && p + 16 <= quint64(data.size()); p += 16) {
                const uchar *d =
                    reinterpret_cast<const uchar *>(data.constData());
                auto rd64 = [&](quint64 off) {
                    const quint32 lo = quint32(d[off] | (d[off + 1] << 8)
                                               | (d[off + 2] << 16)
                                               | (quint32(d[off + 3]) << 24));
                    const quint32 hi =
                        quint32(d[off + 4] | (d[off + 5] << 8)
                                | (d[off + 6] << 16)
                                | (quint32(d[off + 7]) << 24));
                    return quint64(lo) | (quint64(hi) << 32);
                };
                const quint64 tag = rd64(p);
                const quint64 val = rd64(p + 8);
                if (tag == 0) {  // DT_NULL
                    break;
                }
                if (tag != 1) {  // DT_NEEDED
                    continue;
                }
                const quint64 start = strtab.offset + val;
                if (start >= quint64(data.size())) {
                    continue;
                }
                const char *base = data.constData() + start;
                const qint64 max = data.size() - qint64(start);
                out << QString::fromLatin1(base, int(qstrnlen(base, max)));
            }
            break;
        }
        return out;
    }

    Section dynstr() const
    {
        for (int i = 0; i < shnum; ++i) {
            const Section s = section(i);
            if (s.type == 3 && sectionName(s) == QLatin1String(".dynstr")) {
                return s;
            }
        }
        return Section();
    }

    bool hasSection(const QString &name) const
    {
        for (int i = 0; i < shnum; ++i) {
            if (sectionName(section(i)) == name) {
                return true;
            }
        }
        return false;
    }
};

QByteArray readFile(const QString &path)
{
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly)) {
        return QByteArray();
    }
    const QByteArray d = f.readAll();
    f.close();
    return d;
}

QString envOr(const char *name, const QString &fallback = QString())
{
    const QString v = QString::fromLocal8Bit(qgetenv(name));
    return v.isEmpty() ? fallback : v;
}

}  // namespace

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    const QString bin = envOr("SKLADNIK_TEST_BIN");
    const QString dataDir = envOr("SKLADNIK_TEST_DATA_DIR");
    const QString platform = envOr("SKLADNIK_TEST_PLATFORM", "generic");
    const QString expectedVersion =
        envOr("SKLADNIK_EXPECTED_VERSION", "0.5.26042");
    const QStringList libDirs =
        envOr("SKLADNIK_TEST_LIBDIRS").split(QLatin1Char(':'),
                                             Qt::SkipEmptyParts);
    const bool ohos = (platform == QLatin1String("OHOS"));

    if (bin.isEmpty() || dataDir.isEmpty()) {
        std::printf("[FAIL] SKLADNIK_TEST_BIN / SKLADNIK_TEST_DATA_DIR not "
                    "set by the test recipe\n");
        return 2;
    }

    // ---------------- Group A: delivered ELF artifact ----------------
    if (QFileInfo::exists(bin) && QFileInfo(bin).isFile()) {
        pass("installed-executable-present", bin);
    } else {
        fail("installed-executable-present", "missing: " + bin);
        std::printf("\n%d passed, %d failed, %d skipped\n", g_passed,
                    g_failed, g_skipped);
        return 1;
    }

    const Elf64 elf = Elf64::load(bin);
    if (elf.valid) {
        pass("elf64-little-endian-image",
             QStringLiteral("ELFCLASS64 + ELFDATA2LSB"));
    } else {
        fail("elf64-little-endian-image",
             "not a 64-bit little-endian ELF (host-binary leak?)");
    }

    if (elf.valid && elf.machine == 0xB7) {
        pass("elf-machine-aarch64", QStringLiteral("EM_AARCH64 (0xB7)"));
    } else {
        fail("elf-machine-aarch64",
             QStringLiteral("e_machine=0x%1, expected 0xB7")
                 .arg(elf.machine, 0, 16));
    }

    // OHOS musl loader: the default lld 0x10000 max-page-size splits
    // .dynsym/.dynstr into separate high-address RW LOAD segments that the
    // loader refuses to mmap. The recipe pins -Wl,-z,max-page-size=0x1000.
    if (ohos) {
        quint64 worst = 0;
        int loads = 0;
        for (int i = 0; elf.valid && i < elf.phnum; ++i) {
            if (elf.phType(i) != 1) {  // PT_LOAD
                continue;
            }
            ++loads;
            const quint64 align = elf.phField(i, 48);
            if (align > worst) {
                worst = align;
            }
        }
        if (loads > 0 && worst <= 0x1000) {
            pass("ohos-pt-load-page-alignment",
                 QStringLiteral("%1 PT_LOAD, max p_align=0x%2")
                     .arg(loads).arg(worst, 0, 16));
        } else {
            fail("ohos-pt-load-page-alignment",
                 QStringLiteral("%1 PT_LOAD, max p_align=0x%2 (need <=0x1000)")
                     .arg(loads).arg(worst, 0, 16));
        }
    } else {
        skip("ohos-pt-load-page-alignment",
             "OHOS musl loader constraint, platform=" + platform);
    }

    // Every DT_NEEDED must resolve: the OHOS loader resolves path-form
    // NEEDED entries literally with no LD_LIBRARY_PATH fallback, so an
    // unresolvable entry means the game cannot start on device.
    {
        const QStringList needed = elf.needed();
        QStringList unresolved;
        for (const QString &entry : needed) {
            if (entry.startsWith(QLatin1Char('/'))) {
                if (QFileInfo::exists(entry)) {
                    continue;
                }
                unresolved << entry;
                continue;
            }
            bool found = false;
            for (const QString &dir : libDirs) {
                if (QFileInfo::exists(dir + QLatin1Char('/') + entry)) {
                    found = true;
                    break;
                }
            }
            if (!found) {
                unresolved << entry;
            }
        }
        if (needed.isEmpty()) {
            fail("dt-needed-closure-resolves", "no DT_NEEDED entries parsed");
        } else if (unresolved.isEmpty()) {
            pass("dt-needed-closure-resolves",
                 QStringLiteral("%1 DT_NEEDED entries all resolve")
                     .arg(needed.size()));
        } else {
            fail("dt-needed-closure-resolves",
                 QStringLiteral("unresolved: %1").arg(unresolved.join(", ")));
        }
    }

    // OHOS enforces valid ELF code signatures: an unsigned or modified ELF
    // gets EACCES on exec-mapping. The test recipe signs the artifact with
    // binary-sign-tool before running it, so the section must be present.
    if (ohos) {
        if (elf.valid && elf.hasSection(QLatin1String(".codesign"))) {
            pass("ohos-codesign-section-present",
                 QStringLiteral(".codesign present after platform signing"));
        } else {
            fail("ohos-codesign-section-present",
                 "no .codesign section - the artifact would be refused by "
                 "the OHOS loader");
        }
    } else {
        skip("ohos-codesign-section-present",
             "OHOS code-signature enforcement, platform=" + platform);
    }

    // ------------- Group B: the delivered executable runs -------------
    auto runGame = [&](const QStringList &args, QString *out) -> int {
        QProcess proc;
        QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
        env.insert(QStringLiteral("QT_QPA_PLATFORM"),
                   QStringLiteral("offscreen"));
        env.insert(QStringLiteral("HOME"),
                   QDir::temp().filePath(QStringLiteral("skladnik-test-home")));
        if (!libDirs.isEmpty()) {
            QString merged = libDirs.join(QLatin1Char(':'));
            const QString existing =
                env.value(QStringLiteral("LD_LIBRARY_PATH"));
            if (!existing.isEmpty()) {
                merged += QLatin1Char(':') + existing;
            }
            env.insert(QStringLiteral("LD_LIBRARY_PATH"), merged);
        }
        proc.setProcessEnvironment(env);
        proc.setProgram(bin);
        proc.setArguments(args);
        proc.start();
        if (!proc.waitForStarted(30000)) {
            return -1;
        }
        proc.waitForFinished(120000);
        if (out) {
            *out = QString::fromLocal8Bit(proc.readAllStandardOutput())
                + QString::fromLocal8Bit(proc.readAllStandardError());
        }
        return proc.exitStatus() == QProcess::NormalExit ? proc.exitCode() : -1;
    };

    {
        QString out;
        const int rc = runGame({QStringLiteral("--version")}, &out);
        const QString flat = out.simplified();
        if (rc == 0 && flat.contains(expectedVersion)) {
            pass("game-version-runs-offscreen", flat);
        } else {
            fail("game-version-runs-offscreen",
                 QStringLiteral("rc=%1, expected version %2 in output: %3")
                     .arg(rc).arg(expectedVersion, flat));
        }
    }

    // The KIO trim kept the level-collection URL entry point; --help must
    // still advertise the positional URL argument upstream declares.
    {
        QString out;
        const int rc = runGame({QStringLiteral("--help")}, &out);
        if (rc == 0 && out.contains(QLatin1String("URL"))) {
            pass("game-help-advertises-url-argument",
                 QStringLiteral("rc=0, positional URL argument present"));
        } else {
            fail("game-help-advertises-url-argument",
                 QStringLiteral("rc=%1, output: %2").arg(rc).arg(
                     out.simplified()));
        }
    }

    // -------- Group C: installed theme data contract (KGameRenderer) ----
    const QString themes = dataDir + QLatin1String("/themes");
    const QString desktopPath = themes + QLatin1String("/skladnik_classic.desktop");
    const QString svgPath = themes + QLatin1String("/skladnik_classic.svg");

    // src/PlayField.cpp constructs KGameTheme("themes/skladnik_classic.desktop")
    // and reads Type/FileName/VersionFormat from the [KGameTheme] group.
    {
        const QString text = QString::fromUtf8(readFile(desktopPath));
        const bool ok = text.contains(QLatin1String("[KGameTheme]"))
            && text.contains(QRegularExpression(
                   QLatin1String("^Type=SVG$"),
                   QRegularExpression::MultilineOption))
            && text.contains(QRegularExpression(
                   QLatin1String("^FileName=skladnik_classic\\.svg$"),
                   QRegularExpression::MultilineOption))
            && text.contains(QRegularExpression(
                   QLatin1String("^VersionFormat=1$"),
                   QRegularExpression::MultilineOption));
        if (ok) {
            pass("kgametheme-desktop-contract",
                 QStringLiteral("[KGameTheme] Type=SVG FileName=skladnik_classic.svg "
                                "VersionFormat=1"));
        } else {
            fail("kgametheme-desktop-contract",
                 "missing/invalid KGameTheme keys in " + desktopPath);
        }
    }

    const QString svg = QString::fromUtf8(readFile(svgPath));

    // Every renderer element id the game code asks KGameRenderer for must be
    // declared by the installed theme: background (PlayField.cpp), goal /
    // man / saveman / object / treasure and stone_%1 / halfstone_%1
    // (GroundItem.cpp, LARGE_STONES=6 and SMALL_STONES=4).
    {
        QStringList required;
        required << QLatin1String("background") << QLatin1String("goal")
                 << QLatin1String("man") << QLatin1String("saveman")
                 << QLatin1String("object") << QLatin1String("treasure");
        for (int i = 0; i < 6; ++i) {
            required << QStringLiteral("stone_%1").arg(i);
        }
        for (int i = 0; i < 4; ++i) {
            required << QStringLiteral("halfstone_%1").arg(i);
        }
        QStringList missing;
        for (const QString &id : required) {
            if (!svg.contains(QStringLiteral("id=\"%1\"").arg(id))) {
                missing << id;
            }
        }
        if (svg.isEmpty()) {
            fail("theme-svg-declares-renderer-ids",
                 "cannot read " + svgPath);
        } else if (missing.isEmpty()) {
            pass("theme-svg-declares-renderer-ids",
                 QStringLiteral("all %1 renderer element ids declared")
                     .arg(required.size()));
        } else {
            fail("theme-svg-declares-renderer-ids",
                 QStringLiteral("missing ids: %1").arg(missing.join(", ")));
        }
    }

    // KGameRenderer resolves each <image xlink:href="..."> against the
    // installed theme directory.
    QRegularExpression imageRe(
        QLatin1String("<image\\b[^>]*>"), QRegularExpression::DotMatchesEverythingOption);
    QRegularExpression hrefRe(
        QLatin1String("xlink:href=\"([^\"]+)\""));
    QRegularExpression widthRe(QLatin1String("\\bwidth=\"(\\d+)\""));
    QRegularExpression heightRe(QLatin1String("\\bheight=\"(\\d+)\""));

    struct Sprite {
        QString file;
        int w = 0;
        int h = 0;
    };
    QList<Sprite> sprites;
    {
        auto it = imageRe.globalMatch(svg);
        while (it.hasNext()) {
            const QString tag = it.next().captured(0);
            const QRegularExpressionMatch hm = hrefRe.match(tag);
            if (!hm.hasMatch()) {
                continue;
            }
            Sprite s;
            s.file = hm.captured(1);
            const QRegularExpressionMatch wm = widthRe.match(tag);
            const QRegularExpressionMatch hgm = heightRe.match(tag);
            s.w = wm.hasMatch() ? wm.captured(1).toInt() : 0;
            s.h = hgm.hasMatch() ? hgm.captured(1).toInt() : 0;
            sprites << s;
        }
        QStringList missing;
        for (const Sprite &s : sprites) {
            if (!QFileInfo::exists(themes + QLatin1Char('/') + s.file)) {
                missing << s.file;
            }
        }
        if (sprites.isEmpty()) {
            fail("theme-sprites-installed",
                 "no <image> elements parsed from " + svgPath);
        } else if (missing.isEmpty()) {
            pass("theme-sprites-installed",
                 QStringLiteral("all %1 referenced sprites installed in %2")
                     .arg(sprites.size()).arg(themes));
        } else {
            fail("theme-sprites-installed",
                 QStringLiteral("missing: %1").arg(missing.join(", ")));
        }
    }

    // Each sprite must be a real PNG whose IHDR size matches the size the
    // theme SVG declares for it (upstream renders stones at 192x96,
    // half-stones at 96x96 and the remaining sprites at 192x192).
    {
        QStringList bad;
        int checked = 0;
        for (const Sprite &s : sprites) {
            const QByteArray png = readFile(themes + QLatin1Char('/') + s.file);
            static const char magic[8] = {'\x89', 'P', 'N', 'G', '\r', '\n',
                                          '\x1a', '\n'};
            if (png.size() < 33 || std::memcmp(png.constData(), magic, 8) != 0
                || std::memcmp(png.constData() + 12, "IHDR", 4) != 0) {
                bad << s.file + QLatin1String("(not a PNG)");
                continue;
            }
            const uchar *d = reinterpret_cast<const uchar *>(png.constData());
            const int w = (d[16] << 24) | (d[17] << 16) | (d[18] << 8) | d[19];
            const int h = (d[20] << 24) | (d[21] << 16) | (d[22] << 8) | d[23];
            ++checked;
            if (w != s.w || h != s.h) {
                bad << QStringLiteral("%1(%2x%3, svg declares %4x%5)")
                           .arg(s.file).arg(w).arg(h).arg(s.w).arg(s.h);
            }
        }
        if (checked == 0) {
            fail("theme-sprite-png-geometry", "no sprite PNG could be read");
        } else if (bad.isEmpty()) {
            pass("theme-sprite-png-geometry",
                 QStringLiteral("%1 sprite PNGs match their SVG-declared size")
                     .arg(checked));
        } else {
            fail("theme-sprite-png-geometry", bad.join(", "));
        }
    }

    std::printf("\n%d passed, %d failed, %d skipped\n", g_passed, g_failed,
                g_skipped);
    return g_failed == 0 ? 0 : 1;
}
