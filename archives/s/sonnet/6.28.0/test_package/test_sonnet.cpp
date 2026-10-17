/* Sonnet 6.28.0 Consumer Test Suite
 *
 * Verifies the packaged sonnet 6.28.0 on the HarmonyOS PC device through
 * its public consumer surface only:
 *   - KF6::SonnetCore (Speller/Settings/GuessLanguage) in the shipped
 *     no-backend configuration: the no-dictionary contract is asserted
 *     (no language is detected, the query APIs stay quiescent), while the
 *     embedded trigram model itself is exercised by the parsetrigrams6
 *     CLI case below;
 *   - KF6::SonnetUi (Highlighter over a QTextEdit under the offscreen QPA);
 *   - the org.kde.sonnet QML module (SpellcheckHighlighter / Settings);
 *   - the packaged bin/parsetrigrams6 CLI tool.
 *
 * Every check is printed individually; the process exits 1 if any check
 * failed. Spell *correctness* is not asserted: the package intentionally
 * ships without a spell backend (SONNET_NO_BACKENDS), so dictionary-based
 * results are out of scope for this consumer suite.
 */
#include <cstdio>
#include <memory>

#include <QApplication>
#include <QDir>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QFile>
#include <QProcess>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QString>
#include <QStringList>
#include <QTextEdit>

#include <Sonnet/GuessLanguage>
#include <Sonnet/Highlighter>
#include <Sonnet/Settings>
#include <Sonnet/Speller>

static int g_checks = 0;
static int g_failed = 0;

static bool check(const char *description, bool ok)
{
    ++g_checks;
    if (!ok) {
        ++g_failed;
    }
    std::printf("  check: %-58s %s\n", description, ok ? "OK" : "FAILED");
    std::fflush(stdout);
    return ok;
}

/* ---- core: Speller in the no-backend configuration -------------------- */

static void caseSpeller()
{
    Sonnet::Speller speller;
    // Without a backend no dictionary can be loaded, so a default-constructed
    // speller must report itself invalid (Speller::isValid() == !dict()).
    check("Speller default construction loads no dictionary (no backend)",
          !speller.isValid());

    Sonnet::Speller speller2(QStringLiteral("en_US"));
    check("Speller with explicit language loads no dictionary (no backend)",
          !speller2.isValid());
    check("no spell backend is shipped (SONNET_NO_BACKENDS)",
          speller2.availableBackends().isEmpty());

    speller2.setLanguage(QStringLiteral("de_DE"));
    const QString language = speller2.language();
    // Without a backend the tag cannot be resolved to a concrete dictionary;
    // the setter must either keep the plain tag or report the empty
    // "no backend" state - it must not corrupt it into something else.
    check("Speller language setter/getter keeps the tag or reports none",
          language == QLatin1String("de_DE") || language.isEmpty());

    // Documented no-dictionary contract of the query APIs (speller.cpp):
    // isCorrect()/isMisspelled() cannot judge anything and report "not
    // misspelled", suggest() has nothing to offer, and both catalog getters
    // stay empty because the loader serves no clients.
    check("Speller query APIs follow the no-dictionary contract",
          speller2.isCorrect(QStringLiteral("Hello"))
              && !speller2.isMisspelled(QStringLiteral("Helllo"))
              && speller2.suggest(QStringLiteral("Helo")).isEmpty()
              && speller2.availableLanguages().isEmpty()
              && speller2.availableDictionaries().isEmpty());
}

/* ---- core: Settings round-trips through QSettings --------------------- */

static void caseSettings()
{
    Sonnet::Settings settings;

    // SettingsImpl::setDefaultLanguage() only accepts languages the loader
    // can serve (loader->languages() lists the languages of the installed
    // spell backends). With SONNET_NO_BACKENDS that list is empty, so the
    // setter is a no-op and the getter keeps its initial value, which
    // SettingsImpl::restore() seeds from QLocale::system().name().
    const QString languageBefore = settings.defaultLanguage();
    settings.setDefaultLanguage(QStringLiteral("de_DE"));
    check("Settings defaultLanguage setter is a no-op without backends",
          settings.defaultLanguage() == languageBefore);

    // SettingsImpl::setDefaultClient() has the same semantics against
    // loader->clients(), which is empty without backends.
    const QString clientBefore = settings.defaultClient();
    settings.setDefaultClient(QStringLiteral("sonnet-consumer-test"));
    check("Settings defaultClient setter is a no-op without backends",
          settings.defaultClient() == clientBefore);

    settings.setSkipUppercase(true);
    check("Settings skipUppercase true", settings.skipUppercase());
    settings.setSkipUppercase(false);
    check("Settings skipUppercase false", !settings.skipUppercase());

    settings.setAutodetectLanguage(true);
    check("Settings autodetectLanguage true", settings.autodetectLanguage());

    settings.setPreferredLanguages(
        QStringList{QStringLiteral("en"), QStringLiteral("de")});
    check("Settings preferredLanguages round-trip",
          settings.preferredLanguages()
              == QStringList{QStringLiteral("en"), QStringLiteral("de")});

    settings.setCurrentIgnoreList(QStringList{QStringLiteral("zzz")});
    check("Settings currentIgnoreList round-trip",
          settings.currentIgnoreList()
              == QStringList{QStringLiteral("zzz")});
}

/* ---- core: GuessLanguage over the embedded trigram model -------------- */

static void caseGuessLanguage()
{
    Sonnet::GuessLanguage guesser;
    // maxItems=1 with a positive minConfidence yields the single best
    // trigram guess; minConfidence must be > 0 because the accumulation
    // loop condition `confidence < m_minConfidence` is false at 0.0.
    guesser.setLimits(1, 0.1);

    // GuessLanguagePrivate seeds its script->language map from
    // Loader::openLoader()->languages(), i.e. the languages served by the
    // installed spell backends: every script's candidate list is pruned to
    // the languages that actually have a dictionary. With
    // SONNET_NO_BACKENDS the map stays empty, so identify() cannot propose
    // a language even though the trigram models are embedded in the
    // library. Pin down that graceful no-dictionary behavior here; the
    // trigram data pipeline itself is exercised by the parsetrigrams6 case.
    const QString english = guesser.identify(QStringLiteral(
        "This is a longer English sentence written to exercise the embedded "
        "trigram language model of Sonnet GuessLanguage in the HarmonyOS "
        "package."));
    std::printf("  detected (English text): '%s'\n", qPrintable(english));
    check("GuessLanguage yields no candidate for English text without dictionaries",
          english.isEmpty());

    const QString german = guesser.identify(QStringLiteral(
        "Dies ist ein deutscher Satz, der das eingebettete Trigramm-"
        "Sprachmodell von Sonnet GuessLanguage prueft."));
    std::printf("  detected (German text): '%s'\n", qPrintable(german));
    check("GuessLanguage yields no candidate for German text without dictionaries",
          german.isEmpty());
}

/* ---- widgets: Highlighter over a QTextEdit ---------------------------- */

static void caseHighlighter()
{
    QTextEdit edit;
    edit.setPlainText(QStringLiteral(
        "The quick brown fox jumps over the lazy dog."));

    Sonnet::Highlighter highlighter(&edit);
    // QSyntaxHighlighter's constructor attaches to the editor's document;
    // Sonnet::Highlighter must keep that attachment.
    check("Sonnet::Highlighter attaches to the editor's document",
          highlighter.document() == edit.document());
    check("no spell checker plugin is found (no backend shipped)",
          !highlighter.spellCheckerFound());

    edit.setPlainText(QStringLiteral(
        "Hellow world with a misspelled wrod and more text to edit."));
    QCoreApplication::processEvents(QEventLoop::AllEvents, 50);
    // Editing triggers re-highlighting; the highlighter must stay attached
    // and must not conjure up a checker that the package does not ship.
    check("Highlighter stays attached and checker-less while editing",
          highlighter.document() == edit.document()
              && !highlighter.spellCheckerFound());
}

/* ---- QML: org.kde.sonnet module --------------------------------------- */

static void caseQml()
{
    QQmlEngine engine;
    QQmlComponent component(&engine);
    component.setData(QByteArrayLiteral(
                          "import QtQuick\n"
                          "import org.kde.sonnet\n"
                          "Item {\n"
                          "    SpellcheckHighlighter { }\n"
                          "    Settings { }\n"
                          "}\n"),
                      QUrl(QStringLiteral("qrc:/sonnet_consumer_test.qml")));

    // The module plugin may finish resolving asynchronously; wait (bounded)
    // for the component to leave the Loading state.
    QElapsedTimer timer;
    timer.start();
    while (component.status() == QQmlComponent::Loading
           && timer.elapsed() < 30000) {
        QCoreApplication::processEvents(QEventLoop::AllEvents, 50);
    }

    if (!check("org.kde.sonnet component reaches the Ready state",
               component.status() == QQmlComponent::Ready)) {
        std::printf("  qml error: %s\n",
                    qPrintable(component.errorString()));
        return;
    }

    std::unique_ptr<QObject> root(component.create());
    check("org.kde.sonnet root object instantiates", root != nullptr);
    if (!root) {
        std::printf("  qml error: %s\n",
                    qPrintable(component.errorString()));
    }
}

/* ---- CLI: the packaged parsetrigrams6 tool ---------------------------- */

static void caseCliTool()
{
    const QString tool = QString::fromLocal8Bit(qgetenv("PARSETRIGRAMS6_BIN"));
    if (!check("parsetrigrams6 tool is shipped and located",
               !tool.isEmpty() && QFile::exists(tool))) {
        return;
    }

    const QString corpusDir =
        QDir(QDir::homePath()).filePath(QStringLiteral("sonnet-cli-corpus"));
    const QString corpusPath = QDir(corpusDir).filePath(QStringLiteral("en"));
    const QByteArray corpusData("the 9001\n"
                                "qui 1234\n"
                                "bro 567\n"
                                "fox 345\n"
                                "jum 234\n"
                                "son 999\n"
                                "net 888\n");
    // Rewrite the corpus from scratch: a stale file left behind by an
    // earlier run must never be able to fake a success for this one.
    QFile::remove(corpusPath);
    QFile corpus(corpusPath);
    bool corpusReady = QDir().mkpath(corpusDir)
        && corpus.open(QIODevice::WriteOnly | QIODevice::Text);
    if (corpusReady) {
        corpusReady = corpus.write(corpusData) == corpusData.size();
        corpus.close();
    }
    if (!check("parsetrigrams6 corpus file is written", corpusReady)) {
        std::printf("  corpus error: %s\n", qPrintable(corpus.errorString()));
        return;
    }

    QProcess process;
    process.start(tool, QStringList{corpusDir});
    const bool finished = process.waitForFinished(60000);
    const bool cleanExit = finished
        && process.exitStatus() == QProcess::NormalExit
        && process.exitCode() == 0;
    if (!cleanExit) {
        std::printf("  stderr: %s\n",
                    process.readAllStandardError().constData());
    }
    check("parsetrigrams6 exits cleanly over a word corpus", cleanExit);
    check("parsetrigrams6 emits trigram data on stdout",
          !process.readAllStandardOutput().isEmpty());
}

int main(int argc, char **argv)
{
    // One QApplication for the whole suite: the widgets case needs the
    // offscreen QPA, the QML case needs the QtQuick engine.
    QApplication app(argc, argv);

    struct TestCase {
        const char *name;
        void (*fn)();
    };
    const TestCase cases[] = {
        {"core-speller-no-backend", caseSpeller},
        {"core-settings-roundtrip", caseSettings},
        {"core-guesslanguage-embedded-model", caseGuessLanguage},
        {"ui-highlighter-widgets", caseHighlighter},
        {"qml-org-kde-sonnet", caseQml},
        {"cli-parsetrigrams6", caseCliTool},
    };
    const int caseCount = int(sizeof(cases) / sizeof(cases[0]));

    std::printf("Sonnet 6.28.0 Consumer Test Suite\n");
    std::printf("==============================================\n");

    int casesPassed = 0;
    for (const TestCase &testCase : cases) {
        const int failedBefore = g_failed;
        std::printf("== CASE %s\n", testCase.name);
        std::fflush(stdout);
        testCase.fn();
        const bool ok = (g_failed == failedBefore);
        if (ok) {
            ++casesPassed;
        }
        std::printf("TEST %s: %s\n\n", testCase.name, ok ? "PASS" : "FAIL");
        std::fflush(stdout);
    }

    std::printf("TEST SUMMARY: %d/%d cases passed, %d checks, %d failures\n",
                casesPassed, caseCount, g_checks, g_failed);
    return g_failed > 0 ? 1 : 0;
}
