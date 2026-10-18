#include <KColorScheme>

#include <QGuiApplication>

#include <cstdio>

namespace {

int failures = 0;

void check(bool ok, const char *name)
{
    if (ok) {
        std::printf("TEST PASS: %s\n", name);
    } else {
        std::printf("TEST FAIL: %s\n", name);
        ++failures;
    }
}

} // namespace

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);

    const KColorScheme active(QPalette::Active, KColorScheme::View);
    const KColorScheme inactive(QPalette::Inactive, KColorScheme::View);

    check(active.background(KColorScheme::NormalBackground).color().isValid(),
          "active view normal background is valid");
    check(active.foreground(KColorScheme::NormalText).color().isValid(),
          "active view normal text is valid");
    check(active.decoration(KColorScheme::FocusColor).color().isValid(),
          "active view focus decoration is valid");
    check(inactive.background(KColorScheme::NormalBackground).color().isValid(),
          "inactive view normal background is valid");

    const qreal contrast = KColorScheme::contrastF();
    check(contrast >= 0.0 && contrast <= 1.0,
          "contrast factor within [0, 1]");

    std::printf("TEST SUMMARY: %d passed, %d failed\n", 5 - failures, failures);
    return failures == 0 ? 0 : 1;
}
