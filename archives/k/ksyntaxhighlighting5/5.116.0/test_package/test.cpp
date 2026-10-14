// ksyntaxhighlighting5 5.116.0 consumer test (R34: exercises real API).
// Builds a KSyntaxHighlighting::Repository and queries its syntax
// definitions and themes — pure Qt logic that runs without a GUI.
// Assertions are strict: a missing definition or theme is a real FAIL
// (return code 1), never a silently tolerated warning.
#include <KSyntaxHighlighting/Definition>
#include <KSyntaxHighlighting/Repository>
#include <KSyntaxHighlighting/Theme>

#include <QString>
#include <cstdio>

int main()
{
    int failures = 0;

    KSyntaxHighlighting::Repository repo;
    // Force a reload so the bundled syntax definitions (QRC) are indexed;
    // definitionForName() then resolves against the real engine data.
    repo.reload();

    KSyntaxHighlighting::Definition def = repo.definitionForName(QStringLiteral("C++"));
    if (!def.isValid()) {
        std::printf("FAIL: bundled C++ definition not indexed (data path env?)\n");
        ++failures;
    } else {
        std::printf("PASS: definition '%s' section '%s'\n",
                    def.name().toUtf8().constData(),
                    def.section().toUtf8().constData());
    }

    KSyntaxHighlighting::Theme theme = repo.defaultTheme(KSyntaxHighlighting::Repository::LightTheme);
    if (!theme.isValid()) {
        std::printf("FAIL: default light theme is not valid\n");
        ++failures;
    } else {
        std::printf("PASS: default light theme is valid\n");
    }

    if (failures != 0) {
        std::printf("FAIL: %d assertion(s) failed\n", failures);
        return 1;
    }
    std::printf("ALL TESTS PASSED\n");
    return 0;
}
