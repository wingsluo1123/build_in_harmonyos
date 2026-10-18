/*
    SPDX-FileCopyrightText: 2026 ohpc contributors
    SPDX-License-Identifier: MIT
*/
// Consumer-side E2E for the exported KF6Runner CMake package (R34: real
// API usage). The test links only the public surface -- KF6::Runner plus
// Qt6::Core/Qt6::Gui from qtbase -- and drives it on the offscreen
// platform plugin:
//
//   * RunnerSyntax / QueryMatch / RunnerContext value semantics
//   * AbstractRunner subclassing: the documented plugin shape (protected
//     (parent, KPluginMetaData) constructor, match() override adding
//     matches through RunnerContext::addMatch) exercised end to end
//   * RunnerManager construction and the hermetic plugin scan
//
// Every case prints its own TEST PASS/TEST FAIL line; main() returns 1 on
// any failure so conan/ctest report the run as failed (conan test_package
// acceptance gate).
#include <QDir>
#include <QGuiApplication>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTemporaryFile>
#include <QUrl>

#include <KPluginMetaData>

#include <KRunner/AbstractRunner>
#include <KRunner/Action>
#include <KRunner/QueryMatch>
#include <KRunner/RunnerContext>
#include <KRunner/RunnerManager>
#include <KRunner/RunnerSyntax>

#include <cstdio>

using KRunner::AbstractRunner;
using KRunner::Action;
using KRunner::QueryMatch;
using KRunner::RunnerContext;
using KRunner::RunnerManager;
using KRunner::RunnerSyntax;

static int s_pass = 0;
static int s_fail = 0;

static void runCase(const char *name, bool ok)
{
    if (ok) {
        ++s_pass;
        std::printf("TEST PASS: %s\n", name);
    } else {
        ++s_fail;
        std::printf("TEST FAIL: %s\n", name);
    }
}

// The plugin metadata a runner receives from KPluginFactory, written to a
// temporary JSON file in the current directory (the tests run with CWD =
// test_package build folder; /tmp is a read-only erofs on OHOS) and parsed
// back by KPluginMetaData. Any write/parse failure is reported explicitly
// with a DIAG line: an empty metadata would otherwise silently fail
// several unrelated cases with no trace of the cause.
static KPluginMetaData dummyMetaData(bool uniqueResults = false)
{
    QTemporaryFile file(QDir::currentPath() + QStringLiteral("/dummyrunner-XXXXXX.json"));
    if (!file.open()) {
        std::printf("DIAG: dummy metadata temp file open failed: %s (cwd=%s)\n",
                    qUtf8Printable(file.errorString()),
                    qUtf8Printable(QDir::currentPath()));
        return KPluginMetaData();
    }
    QJsonObject kplugin{
        {QStringLiteral("Id"), QStringLiteral("dummyrunner")},
        {QStringLiteral("Name"), QStringLiteral("Dummy Runner")},
        {QStringLiteral("Description"), QStringLiteral("krunner OHOS consumer test runner")},
        {QStringLiteral("Version"), QStringLiteral("1.0")},
        {QStringLiteral("License"), QStringLiteral("MIT")},
        {QStringLiteral("EnabledByDefault"), true},
    };
    QJsonObject root{{QStringLiteral("KPlugin"), kplugin}};
    if (uniqueResults) {
        // Top-level runner metadata key read by AbstractRunnerPrivate.
        root.insert(QStringLiteral("X-Plasma-Runner-Unique-Results"), true);
    }
    file.write(QJsonDocument(root).toJson());
    file.close();
    // KPluginMetaData(const QString &) has QPluginLoader semantics
    // ("reads the plugin metadata from a plugin which can be loaded from
    // the file") and falls back to a file-name-derived id for a plain
    // JSON file (device-verified: valid=0, id=dummyrunner-XXXXXX). The
    // QJsonObject constructor (KPluginMetaData(metaData, fileName), since
    // 6.0) is the documented path for metadata that does not come from a
    // Qt plugin library, and reads the "KPlugin"/"Id" field.
    KPluginMetaData metaData(root, file.fileName());
    std::printf("DIAG: dummy metadata file=%s valid=%d id=%s name=%s unique=%d\n",
                qUtf8Printable(file.fileName()),
                metaData.isValid() ? 1 : 0,
                qUtf8Printable(metaData.pluginId()),
                qUtf8Printable(metaData.name()),
                uniqueResults ? 1 : 0);
    return metaData;
}

// The documented way to write a runner plugin: derive from
// KRunner::AbstractRunner and answer queries from match(). KRunner
// instantiates plugins with the (parent, KPluginMetaData) constructor.
class DummyRunner : public KRunner::AbstractRunner
{
    Q_OBJECT
public:
    DummyRunner(QObject *parent, const KPluginMetaData &metaData)
        : KRunner::AbstractRunner(parent, metaData)
    {
    }

    void match(KRunner::RunnerContext &context) override
    {
        KRunner::QueryMatch match(this);
        match.setId(QStringLiteral("dummy_match_1"));
        match.setText(QStringLiteral("Matched: ") + context.query());
        match.setRelevance(0.85);
        context.addMatch(match);
    }
};

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QCoreApplication::setApplicationName(QStringLiteral("krunner-consumer-test"));
    QCoreApplication::setOrganizationName(QStringLiteral("ohpc"));

    const KPluginMetaData meta = dummyMetaData();
    QObject owner;
    DummyRunner runner(&owner, meta);

    // CASE 01 -- RunnerSyntax: single example query round trip.
    {
        RunnerSyntax syntax(QStringLiteral("dummy query"), QStringLiteral("Runs the dummy query"));
        runCase("runnersyntax_single_query_roundtrip",
                syntax.exampleQueries() == QStringList{QStringLiteral("dummy query")}
                    && syntax.description() == QStringLiteral("Runs the dummy query"));
    }

    // CASE 02 -- RunnerSyntax: multiple example queries keep their order.
    {
        RunnerSyntax syntax(QStringList{QStringLiteral("alpha 1"), QStringLiteral("beta 2")},
                            QStringLiteral("desc"));
        runCase("runnersyntax_multi_query_order",
                syntax.exampleQueries()
                    == QStringList{QStringLiteral("alpha 1"), QStringLiteral("beta 2")});
    }

    // CASE 03 -- RunnerSyntax: copy constructor preserves the content.
    {
        RunnerSyntax original(QStringLiteral("orig query"), QStringLiteral("orig desc"));
        RunnerSyntax copy(original);
        runCase("runnersyntax_copy_ctor",
                copy.exampleQueries() == QStringList{QStringLiteral("orig query")}
                    && copy.description() == QStringLiteral("orig desc"));
    }

    // CASE 04 -- QueryMatch: a default-constructed match is invalid and
    // carries no runner.
    {
        QueryMatch match;
        runCase("querymatch_default_invalid",
                !match.isValid() && match.runner() == nullptr);
    }

    // CASE 05 -- QueryMatch: a match constructed with a runner is valid
    // and reports that runner.
    {
        QueryMatch match(&runner);
        runCase("querymatch_valid_with_runner",
                match.isValid() && match.runner() == &runner);
    }

    // CASE 06 -- AbstractRunner: id()/name() come from the metadata the
    // plugin was constructed with.
    {
        runCase("abstractrunner_id_from_metadata",
                runner.id() == QStringLiteral("dummyrunner")
                    && runner.name() == QStringLiteral("Dummy Runner"));
    }

    // CASE 07 -- QueryMatch: text/subtext round trip.
    {
        QueryMatch match(&runner);
        match.setText(QStringLiteral("Title"));
        match.setSubtext(QStringLiteral("Sub"));
        runCase("querymatch_text_subtext_roundtrip",
                match.text() == QStringLiteral("Title")
                    && match.subtext() == QStringLiteral("Sub"));
    }

    // CASE 08 -- QueryMatch: iconName round trip.
    {
        QueryMatch match(&runner);
        match.setIconName(QStringLiteral("dummy-icon"));
        runCase("querymatch_iconname_roundtrip",
                match.iconName() == QStringLiteral("dummy-icon"));
    }

    // CASE 09 -- QueryMatch: relevance round trip.
    {
        QueryMatch match(&runner);
        match.setRelevance(0.85);
        runCase("querymatch_relevance_roundtrip", match.relevance() == 0.85);
    }

    // CASE 10 -- QueryMatch: data round trip.
    {
        QueryMatch match(&runner);
        match.setData(QVariant(QStringLiteral("payload")));
        runCase("querymatch_data_roundtrip",
                match.data().toString() == QStringLiteral("payload"));
    }

    // CASE 11 -- QueryMatch: without an explicit id the match id falls
    // back to the runner id.
    {
        QueryMatch match(&runner);
        runCase("querymatch_default_id_is_runner_id",
                match.id() == QStringLiteral("dummyrunner"));
    }

    // CASE 12 -- QueryMatch: without the runner declaring
    // X-Plasma-Runner-Unique-Results, setId() yields the composed
    // <runnerId>_<id> form that keeps match ids globally unique across
    // runners (QueryMatchPrivate::setId).
    {
        QueryMatch match(&runner);
        match.setId(QStringLiteral("dummy_match_1"));
        runCase("querymatch_explicit_id_roundtrip",
                match.id() == QStringLiteral("dummyrunner_dummy_match_1"));
    }

    // CASE 13 -- QueryMatch: urls round trip; matches are enabled by
    // default and setEnabled(false) disables them.
    {
        QueryMatch match(&runner);
        const QList<QUrl> urls{QUrl(QStringLiteral("file:///data/x.txt"))};
        match.setUrls(urls);
        const bool urlsOk = match.urls() == urls;
        const bool defaultEnabled = match.isEnabled();
        match.setEnabled(false);
        runCase("querymatch_urls_and_enabled",
                urlsOk && defaultEnabled && !match.isEnabled());
    }

    // CASE 14 -- QueryMatch: multiLine defaults to false and round trips.
    {
        QueryMatch match(&runner);
        const bool defaultOff = !match.isMultiLine();
        match.setMultiLine(true);
        runCase("querymatch_multiline_roundtrip",
                defaultOff && match.isMultiLine());
    }

    // CASE 15 -- QueryMatch: category relevance round trip through the
    // public CategoryRelevance enum.
    {
        QueryMatch match(&runner);
        match.setCategoryRelevance(QueryMatch::CategoryRelevance::High);
        runCase("querymatch_category_relevance",
                match.categoryRelevance() == 70.0);
    }

    // CASE 16 -- QueryMatch: actions set via addAction() round trip.
    {
        QueryMatch match(&runner);
        match.addAction(Action(QStringLiteral("act_id"),
                               QStringLiteral("dummy-icon"),
                               QStringLiteral("Run It")));
        const QList<Action> actions = match.actions();
        runCase("querymatch_actions_add_list",
                actions.size() == 1 && actions.at(0).id() == QStringLiteral("act_id")
                    && actions.at(0).text() == QStringLiteral("Run It"));
    }

    // CASE 17 -- QueryMatch: no action is selected until the manager
    // selects one.
    {
        QueryMatch match(&runner);
        runCase("querymatch_selected_action_null",
                match.selectedAction() == Action());
    }

    // CASE 18 -- AbstractRunner -> RunnerContext E2E: the runner's
    // match() adds its match through the context and every field
    // survives the round trip.
    {
        RunnerContext context;
        context.setQuery(QStringLiteral("hello dummy"));
        runner.match(context);
        const QList<QueryMatch> matches = context.matches();
        bool ok = matches.size() == 1;
        if (ok) {
            const QueryMatch &match = matches.first();
            ok = match.text() == QStringLiteral("Matched: hello dummy")
                && match.id() == QStringLiteral("dummyrunner_dummy_match_1")
                && match.runner() == &runner && match.isValid()
                && match.relevance() == 0.85;
        }
        runCase("dummy_runner_match_roundtrip", ok);
    }

    // CASE 19 -- RunnerContext: a fresh context is valid, setQuery()
    // round trips and addMatch() accepts a match.
    {
        RunnerContext context;
        const bool freshValid = context.isValid();
        context.setQuery(QStringLiteral("q1"));
        QueryMatch match(&runner);
        match.setId(QStringLiteral("m1"));
        const bool added = context.addMatch(match);
        runCase("runnercontext_query_addmatch",
                freshValid && context.query() == QStringLiteral("q1") && added
                    && context.matches().size() == 1);
    }

    // CASE 20 -- RunnerContext: addMatches() appends in order; the ids
    // arrive in the composed <runnerId>_<id> form (CASE 12 semantics).
    {
        RunnerContext context;
        context.setQuery(QStringLiteral("q2"));
        QueryMatch first(&runner);
        first.setId(QStringLiteral("m1"));
        QueryMatch second(&runner);
        second.setId(QStringLiteral("m2"));
        const bool added = context.addMatches(QList<QueryMatch>{first, second});
        const QList<QueryMatch> matches = context.matches();
        runCase("runnercontext_addmatches_order",
                added && matches.size() == 2
                    && matches.at(0).id() == QStringLiteral("dummyrunner_m1")
                    && matches.at(1).id() == QStringLiteral("dummyrunner_m2"));
    }

    // CASE 21 -- RunnerContext: copies share the state (the documented
    // implicitly-shared semantics the manager relies on).
    {
        RunnerContext context;
        context.setQuery(QStringLiteral("shared"));
        QueryMatch match(&runner);
        match.setId(QStringLiteral("shared1"));
        context.addMatch(match);
        RunnerContext copy(context);
        runCase("runnercontext_copy_shares_data",
                copy.query() == QStringLiteral("shared")
                    && copy.matches().size() == 1);
    }

    // CASE 22 -- RunnerManager: constructs under the hermetic XDG roots
    // and finds no runner plugins (XDG_DATA_DIRS points at an empty
    // directory in the test environment).
    {
        RunnerManager manager;
        const QList<AbstractRunner *> runners = manager.runners();
        runCase("runnermanager_no_plugins_hermetic", runners.isEmpty());
    }

    // CASE 23 -- QueryMatch: a runner whose metadata declares the
    // top-level X-Plasma-Runner-Unique-Results key gets the plain id
    // back from setId() (the AbstractRunnerPrivate::hasUniqueResults
    // branch of QueryMatchPrivate::setId).
    {
        const KPluginMetaData uniqueMeta = dummyMetaData(/*uniqueResults=*/true);
        QObject uniqueOwner;
        DummyRunner uniqueRunner(&uniqueOwner, uniqueMeta);
        QueryMatch match(&uniqueRunner);
        match.setId(QStringLiteral("unique_match_1"));
        runCase("querymatch_unique_results_plain_id",
                match.id() == QStringLiteral("unique_match_1"));
    }

    std::printf("SUMMARY: %d passed, %d failed\n", s_pass, s_fail);
    return s_fail == 0 ? 0 : 1;
}

#include "test_krunner.moc"
