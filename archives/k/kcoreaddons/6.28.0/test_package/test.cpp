/* Consumer-side end-to-end executor for the packaged kcoreaddons library.
 *
 * The executable finds and links KF6::CoreAddons through the installed
 * KF6CoreAddonsConfig.cmake and only uses headers installed by the package,
 * so it cannot build or pass when the package is missing or stale (R34).
 *
 * Every case runs independently and reports TEST PASS / TEST FAIL on its own
 * line; the last line is a machine-readable summary and the process exit code
 * is non-zero when any case fails.
 */
#include <KAboutData>
#include <KFormat>
#include <KStringHandler>
#include <QCoreApplication>
#include <QString>
#include <cstdio>

static int g_cases_run = 0;
static int g_cases_failed = 0;
static int g_case_failed = 0;
static int g_checks = 0;
static int g_check_failures = 0;

static void begin_case(const char *name)
{
    g_case_failed = 0;
    std::printf("== case: %s\n", name);
    std::fflush(stdout);
}

static void check(bool ok, const char *what)
{
    g_checks++;
    if (!ok) {
        g_case_failed = 1;
        g_check_failures++;
        std::printf("  CHECK FAIL: %s\n", what);
    }
}

static void end_case(const char *name)
{
    g_cases_run++;
    if (g_case_failed) {
        g_cases_failed++;
        std::printf("TEST FAIL: %s\n", name);
    } else {
        std::printf("TEST PASS: %s\n", name);
    }
    std::fflush(stdout);
}

/* --- case 1: KAboutData identity fields round-trip ------------------------- */
static void case_kaboutdata_identity(void)
{
    KAboutData about(QStringLiteral("testapp"),
                     QStringLiteral("Test App"),
                     QStringLiteral("1.2.3"));
    check(about.componentName() == QStringLiteral("testapp"),
          "componentName round-trip");
    check(about.displayName() == QStringLiteral("Test App"),
          "displayName round-trip");
    check(about.version() == QStringLiteral("1.2.3"),
          "version round-trip");
}

/* --- case 2: author bookkeeping -------------------------------------------- */
static void case_kaboutdata_authors(void)
{
    KAboutData about(QStringLiteral("testapp"),
                     QStringLiteral("Test App"),
                     QStringLiteral("1.2.3"));
    check(about.authors().isEmpty(), "fresh KAboutData has no authors");
    about.addAuthor(KAboutPerson(QStringLiteral("Test Person"),
                                 QStringLiteral("Tester"),
                                 QStringLiteral("test@example.com")));
    check(about.authors().size() == 1, "one author after addAuthor");
    const auto authors = about.authors();
    if (!authors.isEmpty()) {
        const KAboutPerson &a = authors.first();
        check(a.name() == QStringLiteral("Test Person"),
              "author name round-trip");
        check(a.emailAddress() == QStringLiteral("test@example.com"),
              "author email round-trip");
    }
}

/* --- case 3: KFormat human-readable byte sizes ----------------------------- */
static void case_kformat_byte_size(void)
{
    KFormat fmt;
    const QString kib = fmt.formatByteSize(2048);
    const QString mib = fmt.formatByteSize(2 * 1024 * 1024);
    check(kib.contains(QStringLiteral("KiB")),
          "formatByteSize(2048) reports KiB unit");
    check(mib.contains(QStringLiteral("MiB")),
          "formatByteSize(2 MiB) reports MiB unit");
}

/* --- case 4: KStringHandler text helpers ----------------------------------- */
static void case_kstringhandler_obscure(void)
{
    const QString pw = QStringLiteral("abc123!");
    const QString obscured = KStringHandler::obscure(pw);
    check(obscured.size() == pw.size(),
          "obscure() keeps the length of the input");
    check(obscured != pw,
          "obscure() transforms the input");
    check(KStringHandler::obscure(obscured) == pw,
          "obscure() is reversible (scrambling is an involution)");
    const QByteArray obscuredBytes = obscured.toUtf8();
    check(KStringHandler::obscure(QString::fromUtf8(obscuredBytes.constData())) == pw,
          "obscure() round-trips through UTF-8 (upstream bug 167900 contract)");
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    static const struct {
        const char *name;
        void (*fn)(void);
    } cases[] = {
        {"kaboutdata_identity", case_kaboutdata_identity},
        {"kaboutdata_authors", case_kaboutdata_authors},
        {"kformat_byte_size", case_kformat_byte_size},
        {"kstringhandler_obscure", case_kstringhandler_obscure},
    };
    const int n = (int) (sizeof(cases) / sizeof(cases[0]));

    std::printf("kcoreaddons consumer E2E executor (%d cases)\n", n);
    for (int i = 0; i < n; i++) {
        begin_case(cases[i].name);
        cases[i].fn();
        end_case(cases[i].name);
    }
    std::printf("checks executed: %d, check failures: %d\n",
                g_checks, g_check_failures);
    std::printf("TEST SUMMARY: %d passed, %d failed\n",
                g_cases_run - g_cases_failed, g_cases_failed);
    return g_cases_failed ? 1 : 0;
}
