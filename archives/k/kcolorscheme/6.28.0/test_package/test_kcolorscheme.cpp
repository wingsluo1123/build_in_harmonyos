// Consumer E2E for the installed KF6ColorScheme package: real public-API
// usage of KColorScheme / KStatefulBrush through the exported CMake
// package (find_package(KF6ColorScheme) -> KF6::ColorScheme), driven
// headless under QT_QPA_PLATFORM=offscreen. One TEST PASS/FAIL line per
// case (jakarta-authentication-api 3.0.0 precedent); any failure exits
// with status 1 so both the direct run and the ctest gate go red.

#include <KColorScheme>
#include <KStatefulBrush>

#include <QBrush>
#include <QColor>
#include <QGuiApplication>
#include <QPalette>

#include <cstdio>

static int g_passed = 0;
static int g_failed = 0;

static void check(const char *name, bool ok)
{
    if (ok) {
        ++g_passed;
        std::printf("TEST PASS: %s\n", name);
    } else {
        ++g_failed;
        std::printf("TEST FAIL: %s\n", name);
    }
}

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);

    static const char *const setNames[KColorScheme::NColorSets] = {
        "View", "Window", "Button", "Selection",
        "Tooltip", "Complementary", "Header",
    };

    // View-set background/foreground/decoration lookups under the active
    // widget state.
    const KColorScheme view(QPalette::Active, KColorScheme::View);
    const QColor viewBackground =
        view.background(KColorScheme::NormalBackground).color();
    check("view/normalBackground valid", viewBackground.isValid());
    check("view/normalText valid",
          view.foreground(KColorScheme::NormalText).color().isValid());
    check("view/focusColor valid",
          view.decoration(KColorScheme::FocusColor).color().isValid());
    check("view/hoverColor valid",
          view.decoration(KColorScheme::HoverColor).color().isValid());

    // Contrast factors are documented between 0.0 and 1.0.
    const qreal contrast = KColorScheme::contrastF();
    check("contrastF in [0,1]", contrast >= 0.0 && contrast <= 1.0);
    const qreal frameContrast = KColorScheme::frameContrast();
    check("frameContrast in [0,1]",
          frameContrast >= 0.0 && frameContrast <= 1.0);

    // Every ColorSet yields a valid normal background and normal text.
    for (int set = 0; set < KColorScheme::NColorSets; ++set) {
        const KColorScheme scheme(QPalette::Active,
                                  static_cast<KColorScheme::ColorSet>(set));
        char name[64];
        std::snprintf(name, sizeof(name), "set %s/normalBackground valid",
                      setNames[set]);
        check(name, scheme.background().color().isValid());
        std::snprintf(name, sizeof(name), "set %s/normalText valid",
                      setNames[set]);
        check(name, scheme.foreground().color().isValid());
    }

    // The inactive widget state resolves too.
    const KColorScheme inactive(QPalette::Inactive, KColorScheme::Window);
    check("inactive window/normalBackground valid",
          inactive.background().color().isValid());

    // KStatefulBrush constructor overloads resolve and yield per-state
    // brushes; the default-constructed brush returns a null QBrush per
    // the class documentation.
    const KStatefulBrush backgroundBrush(KColorScheme::View,
                                         KColorScheme::NormalBackground);
    check("KStatefulBrush(view, background) valid",
          backgroundBrush.brush(QPalette::Active).color().isValid());
    const KStatefulBrush foregroundBrush(KColorScheme::View,
                                         KColorScheme::NormalText);
    check("KStatefulBrush(view, foreground) valid",
          foregroundBrush.brush(QPalette::Active).color().isValid());
    const KStatefulBrush decorationBrush(KColorScheme::View,
                                         KColorScheme::FocusColor);
    check("KStatefulBrush(view, decoration) valid",
          decorationBrush.brush(QPalette::Active).color().isValid());
    check("KStatefulBrush() default yields no brush",
          KStatefulBrush().brush(QPalette::Active).style() == Qt::NoBrush);

    // Static and member shade overloads produce real colors.
    check("static shade(color, MidShade) valid",
          KColorScheme::shade(QColor(128, 128, 128),
                              KColorScheme::MidShade).isValid());
    check("member shade(DarkShade) valid",
          view.shade(KColorScheme::DarkShade).isValid());

    // adjustBackground rewrites the palette entry with exactly the
    // scheme's background color for that state.
    QPalette palette;
    KColorScheme::adjustBackground(palette, KColorScheme::NormalBackground,
                                   QPalette::Base, KColorScheme::View);
    const QColor paletteColor = palette.color(QPalette::Active, QPalette::Base);
    if (paletteColor != viewBackground) {
        std::printf("DIAG: palette=%s scheme=%s\n",
                    paletteColor.name().toUtf8().constData(),
                    viewBackground.name().toUtf8().constData());
    }
    check("adjustBackground sets the scheme color",
          paletteColor == viewBackground);

    // Copy semantics: operator== holds for a copy of the same scheme.
    const KColorScheme copy = view;
    check("copy compares equal", copy == view);

    std::printf("TEST SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
