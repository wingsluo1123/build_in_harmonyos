// kguiaddons 6.28.0 consumer test (R34: exercises the installed package
// through its public CamelCase headers, not the build tree).
//
// Runs eight consumer-level cases against the published package:
//   1. kcolorutils-lighten-darken    - lighten/darken direction and validity
//   2. kcolorutils-contrast-ratio    - WCAG contrast ratio invariants
//   3. kcolorutils-mix-tint          - mix/tint blend direction and bounds
//   4. kcolorutils-hcy-roundtrip     - getHcy/hcyColor round-trip
//   5. kcolorutils-overlay-colors    - opaque-overlay identity semantics
//   6. kwordwrap-truncation          - KWordWrap truncation and wrapping
//   7. kiconutils-addoverlay         - KIconUtils::addOverlay rendering
//   8. kcountryflagemojiiconengine   - flag emoji icon engine rendering
#include <KColorUtils>
#include <KCountryFlagEmojiIconEngine>
#include <KIconUtils>
#include <KWordWrap>

#include <QFont>
#include <QFontMetrics>
#include <QGuiApplication>
#include <QIcon>
#include <QImage>
#include <QPixmap>
#include <QRect>
#include <QString>

#include <cmath>
#include <cstdio>

static int g_passed = 0;
static int g_failed = 0;

static void report(const bool ok, const char *name, const QString &detail)
{
    if (ok) {
        ++g_passed;
        std::printf("TEST PASS: %s\n", name);
    } else {
        ++g_failed;
        std::printf("TEST FAIL: %s%s\n", name,
                    detail.isEmpty() ? "" : (" -- " + detail).toUtf8().constData());
    }
}

static QString channelDiff(const QColor &a, const QColor &b)
{
    return QStringLiteral("a=(%1,%2,%3) b=(%4,%5,%6)")
        .arg(a.red())
        .arg(a.green())
        .arg(a.blue())
        .arg(b.red())
        .arg(b.green())
        .arg(b.blue());
}

// 1. lighten() raises luma, darken() lowers it; both stay valid colors.
static bool caseLightenDarken(QString *detail)
{
    const QColor base(0x2a, 0x82, 0xda);
    const QColor lighter = KColorUtils::lighten(base, 0.1);
    const QColor darker = KColorUtils::darken(base, 0.1);
    if (!lighter.isValid() || !darker.isValid()) {
        *detail = QStringLiteral("lighten/darken returned an invalid color");
        return false;
    }
    if (KColorUtils::luma(lighter) <= KColorUtils::luma(base)) {
        *detail = QStringLiteral("lighten did not raise luma");
        return false;
    }
    if (KColorUtils::luma(darker) >= KColorUtils::luma(base)) {
        *detail = QStringLiteral("darken did not lower luma");
        return false;
    }
    return true;
}

// 2. contrastRatio(): black/white == 21.0, black/black == 1.0 (both orders).
static bool caseContrastRatio(QString *detail)
{
    const qreal bw = KColorUtils::contrastRatio(Qt::black, Qt::white);
    const qreal wb = KColorUtils::contrastRatio(Qt::white, Qt::black);
    const qreal bb = KColorUtils::contrastRatio(Qt::black, Qt::black);
    const qreal ww = KColorUtils::contrastRatio(Qt::white, Qt::white);
    if (std::fabs(bw - 21.0) > 0.001 || std::fabs(wb - 21.0) > 0.001) {
        *detail = QStringLiteral("contrastRatio(black,white)=%1 / (white,black)=%2, expected 21.0")
                      .arg(bw)
                      .arg(wb);
        return false;
    }
    if (std::fabs(bb - 1.0) > 0.001 || std::fabs(ww - 1.0) > 0.001) {
        *detail = QStringLiteral("contrastRatio same-color = %1 / %2, expected 1.0").arg(bb).arg(ww);
        return false;
    }
    return true;
}

// 3. mix() blends toward the brighter color; tint() respects its 0/1 bounds
//    and raises luma when blending toward white.
static bool caseMixTint(QString *detail)
{
    const QColor base(0x2a, 0x82, 0xda);
    const QColor mixed = KColorUtils::mix(base, Qt::white, 0.5);
    const qreal baseLuma = KColorUtils::luma(base);
    const qreal mixedLuma = KColorUtils::luma(mixed);
    if (!(mixedLuma > baseLuma && mixedLuma < KColorUtils::luma(Qt::white))) {
        *detail = QStringLiteral("mix(base,white,0.5) luma %1 not between base %2 and white 1.0")
                      .arg(mixedLuma)
                      .arg(baseLuma);
        return false;
    }
    if (KColorUtils::tint(base, Qt::white, 0.0) != base) {
        *detail = QStringLiteral("tint(amount=0) did not return the base color");
        return false;
    }
    if (KColorUtils::tint(base, Qt::white, 1.0) != QColor(Qt::white)) {
        *detail = QStringLiteral("tint(amount=1) did not return the color");
        return false;
    }
    const QColor tinted = KColorUtils::tint(base, Qt::white, 0.5);
    if (KColorUtils::luma(tinted) <= baseLuma) {
        *detail = QStringLiteral("tint(base,white,0.5) luma %1 not above base %2")
                      .arg(KColorUtils::luma(tinted))
                      .arg(baseLuma);
        return false;
    }
    return true;
}

// 4. getHcy() reports sane HCY components and hcyColor() rebuilds the input.
static bool caseHcyRoundtrip(QString *detail)
{
    const QColor base(0x2a, 0x82, 0xda);
    qreal h = -1.0;
    qreal c = -1.0;
    qreal y = -1.0;
    qreal a = -1.0;
    KColorUtils::getHcy(base, &h, &c, &y, &a);
    if (!(h >= 0.0 && h < 360.0) || !(c >= 0.0 && c <= 1.0) || !(y >= 0.0 && y <= 1.0)
        || std::fabs(a - 1.0) > 0.001) {
        *detail = QStringLiteral("getHcy out of range: h=%1 c=%2 y=%3 a=%4").arg(h).arg(c).arg(y).arg(a);
        return false;
    }
    const QColor rt = KColorUtils::hcyColor(h, c, y, a);
    if (!rt.isValid()) {
        *detail = QStringLiteral("hcyColor returned an invalid color");
        return false;
    }
    if (qAbs(rt.red() - base.red()) > 2 || qAbs(rt.green() - base.green()) > 2
        || qAbs(rt.blue() - base.blue()) > 2) {
        *detail = QStringLiteral("hcy round-trip differs by more than 2/255 -- %1").arg(channelDiff(rt, base));
        return false;
    }
    return true;
}

// 5. overlayColors(): an opaque paint replaces the base exactly; a fully
//    transparent paint leaves the (opaque) base untouched.
static bool caseOverlayColors(QString *detail)
{
    const QColor color1(10, 10, 100);
    const QColor color2(10, 10, 160);
    const QColor blended = KColorUtils::overlayColors(color1, color2);
    if (blended != color2) {
        *detail = QStringLiteral("opaque overlay != paint color -- %1").arg(channelDiff(blended, color2));
        return false;
    }
    const QColor transparent = KColorUtils::overlayColors(color1, Qt::transparent);
    if (transparent.red() != color1.red() || transparent.green() != color1.green()
        || transparent.blue() != color1.blue()) {
        *detail = QStringLiteral("transparent overlay changed the base -- %1").arg(channelDiff(transparent, color1));
        return false;
    }
    return true;
}

// 6. KWordWrap: narrow rectangles truncate with an ellipsis, a very wide
//    rectangle preserves pre-existing newlines (mirrors the upstream checks).
static bool caseWordWrap(QString *detail)
{
    const QFont font(QStringLiteral("helvetica"), 12);
    // KWordWrap::formatText takes QFontMetrics& (non-const); mirror the
    // upstream autotest, which also builds a mutable QFontMetrics.
    QFontMetrics fm(font);

    QRect r(0, 0, 100, -1);
    const QString longText = QStringLiteral("test wadabada [/foo/bar/waba] and some more text here");
    KWordWrap ww = KWordWrap::formatText(fm, r, 0, longText);
    if (!ww.truncatedString().endsWith(QStringLiteral("..."))) {
        *detail = QStringLiteral("narrow rect did not truncate: '%1'").arg(ww.truncatedString());
        return false;
    }

    const QString tagText = QStringLiteral("</p></p></p></p>");
    for (int width = 100; width > 0; width -= 10) {
        r.setWidth(width);
        ww = KWordWrap::formatText(fm, r, 0, tagText);
        if (!ww.truncatedString().endsWith(QStringLiteral("..."))) {
            *detail = QStringLiteral("width %1 did not truncate tag text").arg(width);
            return false;
        }
    }

    r.setWidth(1000);
    const QString multiline = QStringLiteral("The title here\nFoo (bar)\nFoo2 (bar2)");
    ww = KWordWrap::formatText(fm, r, 0, multiline);
    if (ww.wrappedString() != multiline) {
        *detail = QStringLiteral("wide rect changed the text: '%1'").arg(ww.wrappedString());
        return false;
    }
    return true;
}

// 7. KIconUtils::addOverlay(): a blue overlay renders over the red base icon;
//    a null overlay renders the base with no overlay pixels.
static bool caseAddOverlay(QString *detail)
{
    QPixmap rectanglePixmap(32, 32);
    rectanglePixmap.fill(Qt::red);
    const QIcon icon(rectanglePixmap);

    QPixmap overlay(32, 32);
    overlay.fill(Qt::blue);
    const QIcon overlayIcon(overlay);

    const QIcon combined = KIconUtils::addOverlay(icon, overlayIcon, Qt::BottomRightCorner);
    const QImage result = combined.pixmap(32, 32).toImage();
    int bluePixels = 0;
    int redPixels = 0;
    for (int px = 0; px < result.width(); ++px) {
        for (int py = 0; py < result.height(); ++py) {
            const QRgb pixel = result.pixel(px, py);
            if (qRed(pixel) == 255) {
                ++redPixels;
            } else if (qBlue(pixel) == 255) {
                ++bluePixels;
            }
        }
    }
    if (bluePixels == 0) {
        *detail = QStringLiteral("overlay render has no blue pixels");
        return false;
    }
    if (redPixels == 0) {
        *detail = QStringLiteral("overlay render lost the base icon (no red pixels)");
        return false;
    }

    // Unsetting the overlay (a null QIcon) must render the base with no
    // overlay pixels. The engine composes through QPainter, so verify the
    // render's own pixels (the counting style the upstream autotest uses)
    // rather than byte-comparing two different render paths.
    const QIcon cleared = KIconUtils::addOverlay(icon, QIcon(), Qt::BottomRightCorner);
    const QImage clearedRender = cleared.pixmap(32, 32).toImage();
    int clearedBlue = 0;
    int clearedRed = 0;
    for (int px = 0; px < clearedRender.width(); ++px) {
        for (int py = 0; py < clearedRender.height(); ++py) {
            const QRgb pixel = clearedRender.pixel(px, py);
            if (qBlue(pixel) == 255) {
                ++clearedBlue;
            } else if (qRed(pixel) == 255 && qAlpha(pixel) == 255) {
                ++clearedRed;
            }
        }
    }
    if (clearedBlue != 0) {
        *detail = QStringLiteral("null overlay still rendered blue pixels: %1").arg(clearedBlue);
        return false;
    }
    if (clearedRed != 32 * 32) {
        *detail = QStringLiteral("null overlay render is not fully opaque red: %1 of %2 pixels")
                      .arg(clearedRed)
                      .arg(32 * 32);
        return false;
    }
    return true;
}

// 8. KCountryFlagEmojiIconEngine: the empty string is null; a country code
//    (and a subdivision / region code) renders a non-null pixmap.
static bool caseCountryFlagEmoji(QString *detail)
{
    if (!KCountryFlagEmojiIconEngine(QString()).isNull()) {
        *detail = QStringLiteral("empty code was not reported as null");
        return false;
    }
    const QString codes[] = {QStringLiteral("AT"), QStringLiteral("GB-SCT"), QStringLiteral("LATAM")};
    for (const QString &code : codes) {
        const QIcon icon(new KCountryFlagEmojiIconEngine(code));
        if (icon.pixmap(16, 16).isNull()) {
            *detail = QStringLiteral("pixmap for '%1' is null").arg(code);
            return false;
        }
    }
    return true;
}

struct TestCase {
    const char *name;
    bool (*run)(QString *detail);
};

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);

    const TestCase cases[] = {
        {"kcolorutils-lighten-darken", caseLightenDarken},
        {"kcolorutils-contrast-ratio", caseContrastRatio},
        {"kcolorutils-mix-tint", caseMixTint},
        {"kcolorutils-hcy-roundtrip", caseHcyRoundtrip},
        {"kcolorutils-overlay-colors", caseOverlayColors},
        {"kwordwrap-truncation", caseWordWrap},
        {"kiconutils-addoverlay", caseAddOverlay},
        {"kcountryflagemojiiconengine", caseCountryFlagEmoji},
    };

    for (const TestCase &testCase : cases) {
        QString detail;
        const bool ok = testCase.run(&detail);
        report(ok, testCase.name, detail);
    }

    std::printf("TEST SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed ? 1 : 0;
}
