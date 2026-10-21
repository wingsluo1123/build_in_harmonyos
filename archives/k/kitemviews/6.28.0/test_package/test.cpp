// kitemviews 6.28.0 consumer end-to-end test (R34: exercises the packaged API).
//
// Three consumer cases run headless (QT_QPA_PLATFORM=offscreen is set by the
// test harness):
//   1. KTreeWidgetSearchLine incremental-filtering a QTreeWidget, including
//      the keepParentsVisible semantics (a parent is kept visible for a
//      matching descendant; a non-matching child stays hidden).
//   2. KListWidgetSearchLine filtering a QListWidget (case-insensitive).
//   3. KCategorizedView + KCategorizedSortFilterProxyModel + KCategoryDrawer
//      categorized rendering flow.
//
// Every case reports TEST PASS / TEST FAIL independently; the process prints
// "TEST SUMMARY: N passed, M failed" and exits non-zero if any case failed,
// so the Conan test step fails on any regression.

#include <KCategorizedSortFilterProxyModel>
#include <KCategorizedView>
#include <KCategoryDrawer>
#include <KListWidgetSearchLine>
#include <KTreeWidgetSearchLine>

#include <QApplication>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QListWidget>
#include <QStandardItemModel>
#include <QTreeWidget>

#include <cstdio>
#include <functional>

static int gChecks = 0;
static int gFailedChecks = 0;
static int gCases = 0;
static int gCasesPassed = 0;

static void check(bool ok, const char *what)
{
    ++gChecks;
    if (ok) {
        std::printf("  [check] OK   %s\n", what);
    } else {
        ++gFailedChecks;
        std::printf("  [check] FAIL %s\n", what);
    }
}

// Search lines debounce filtering with a ~200 ms timer, so spin the event
// loop until the expected observable state shows up (bounded wait).
static void waitFor(const std::function<bool()> &cond, int timeoutMs = 3000)
{
    QElapsedTimer t;
    t.start();
    while (!cond() && t.elapsed() < timeoutMs) {
        QCoreApplication::processEvents(QEventLoop::AllEvents, 50);
    }
}

static void runCase(const char *name, void (*body)())
{
    ++gCases;
    std::printf("TEST CASE: %s\n", name);
    const int before = gFailedChecks;
    body();
    if (gFailedChecks == before) {
        ++gCasesPassed;
        std::printf("TEST PASS: %s\n", name);
    } else {
        std::printf("TEST FAIL: %s\n", name);
    }
}

static void caseTreeSearchLine()
{
    QTreeWidget tree;
    tree.setColumnCount(1);
    auto *apple = new QTreeWidgetItem(&tree, QStringList() << QStringLiteral("apple"));
    auto *banana = new QTreeWidgetItem(&tree, QStringList() << QStringLiteral("banana"));
    auto *blueberry = new QTreeWidgetItem(banana, QStringList() << QStringLiteral("blueberry"));
    auto *cherry = new QTreeWidgetItem(&tree, QStringList() << QStringLiteral("cherry"));
    auto *melon = new QTreeWidgetItem(cherry, QStringList() << QStringLiteral("melon"));

    KTreeWidgetSearchLine searchLine(nullptr, &tree);
    check(searchLine.treeWidget() == &tree, "search line is wired to the tree widget");

    int updates = 0;
    QObject::connect(&searchLine, &KTreeWidgetSearchLine::searchUpdated,
                     [&updates](const QString &) { ++updates; });

    searchLine.setText(QStringLiteral("ban"));
    waitFor([&] { return updates >= 1 && apple->isHidden(); });
    check(updates >= 1, "searchUpdated signal fired (debounced update path)");
    check(!banana->isHidden(), "'banana' matches 'ban' and stays visible");
    check(apple->isHidden(), "unrelated top-level 'apple' is hidden");
    check(cherry->isHidden(), "unrelated top-level 'cherry' is hidden");
    check(blueberry->isHidden(), "non-matching child of a matching parent is still hidden");

    searchLine.setText(QStringLiteral("berry"));
    waitFor([&] { return !blueberry->isHidden(); });
    check(!blueberry->isHidden(), "'blueberry' matches 'berry'");
    check(!banana->isHidden(), "parent 'banana' is kept for its matching child");
    check(apple->isHidden(), "'apple' stays hidden after retyping");

    searchLine.setText(QStringLiteral("melon"));
    waitFor([&] { return !cherry->isHidden(); });
    check(!cherry->isHidden(), "parent 'cherry' is kept for child 'melon'");
    check(!melon->isHidden(), "'melon' itself matches and is visible");
    check(banana->isHidden(), "the 'banana' family is hidden once 'melon' replaces 'berry'");

    searchLine.clear();
    waitFor([&] { return !apple->isHidden() && !cherry->isHidden(); });
    check(!apple->isHidden() && !banana->isHidden() && !cherry->isHidden(),
          "clearing the search restores every row");
}

static void caseListSearchLine()
{
    QListWidget list;
    list.addItem(QStringLiteral("aardvark"));
    list.addItem(QStringLiteral("banana"));
    list.addItem(QStringLiteral("cherry"));

    KListWidgetSearchLine searchLine(nullptr, &list);
    check(searchLine.listWidget() == &list, "search line is wired to the list widget");

    searchLine.setText(QStringLiteral("ban"));
    waitFor([&] { return list.item(0)->isHidden(); });
    check(!list.item(1)->isHidden(), "'banana' stays visible for 'ban'");
    check(list.item(0)->isHidden() && list.item(2)->isHidden(),
          "non-matching rows are hidden");

    searchLine.setText(QStringLiteral("CHERRY"));
    waitFor([&] { return !list.item(2)->isHidden(); });
    check(!list.item(2)->isHidden(), "case-insensitive match for 'CHERRY'");
    check(list.item(1)->isHidden(), "'banana' is hidden once 'CHERRY' replaces 'ban'");

    searchLine.clear();
    waitFor([&] { return !list.item(0)->isHidden(); });
    check(!list.item(0)->isHidden() && !list.item(1)->isHidden(),
          "clearing the search restores every row");
}

static void caseCategorizedView()
{
    QStandardItemModel model;
    const struct {
        const char *text;
        const char *category;
    } rows[] = {
        {"Avocado", "Fruits"}, {"Fig", "Fruits"},  {"Mango", "Fruits"},
        {"Kale", "Veggies"},   {"Pea", "Veggies"}, {"Leek", "Veggies"},
    };

    KCategorizedSortFilterProxyModel proxy;
    proxy.setCategorizedModel(true);
    proxy.setSourceModel(&model);

    KCategorizedView view;
    view.setModel(&proxy);
    check(view.model() == &proxy, "categorized view adopts the proxy model");

    KCategoryDrawer drawer(&view);
    view.setCategoryDrawer(&drawer);
    check(view.categoryDrawer() == &drawer, "category drawer is wired to the view");

    // Populate the source model only after the view is wired up. This is the
    // canonical usage pattern: the view builds its category bookkeeping from
    // the model's rowsInserted/layoutChanged signals, so rows that exist
    // before setModel() are never indexed into blocks.
    for (const auto &row : rows) {
        auto *item = new QStandardItem(QString::fromLatin1(row.text));
        item->setData(QString::fromLatin1(row.category),
                      KCategorizedSortFilterProxyModel::CategoryDisplayRole);
        item->setData(QString::fromLatin1(row.category),
                      KCategorizedSortFilterProxyModel::CategorySortRole);
        model.appendRow(item);
    }
    proxy.sort(0);

    check(proxy.isCategorizedModel(), "proxy reports categorized mode");
    check(proxy.rowCount() == 6, "all six rows survive the proxy");
    check(proxy.data(proxy.index(0, 0),
                     KCategorizedSortFilterProxyModel::CategoryDisplayRole)
                  .toString()
              == QStringLiteral("Fruits"),
          "sorting groups 'Fruits' before 'Veggies'");
    check(proxy.data(proxy.index(5, 0),
                     KCategorizedSortFilterProxyModel::CategoryDisplayRole)
                  .toString()
              == QStringLiteral("Veggies"),
          "the last row belongs to the 'Veggies' block");

    view.resize(640, 480);
    view.show();
    // The view computes each block's height lazily while painting, so give
    // the event loop a chance to run a paint pass before asking for blocks.
    waitFor([&] {
        return view.block(QStringLiteral("Fruits")).size() == 3
            && view.block(QStringLiteral("Veggies")).size() == 3;
    });
    check(view.block(QStringLiteral("Fruits")).size() == 3,
          "block('Fruits') lists its three rows after layout");
    check(view.block(QStringLiteral("Veggies")).size() == 3,
          "block('Veggies') lists its three rows after layout");
    view.hide();
}

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    std::printf("== kitemviews 6.28.0 consumer end-to-end test ==\n");
    runCase("KTreeWidgetSearchLine filters a QTreeWidget", caseTreeSearchLine);
    runCase("KListWidgetSearchLine filters a QListWidget", caseListSearchLine);
    runCase("KCategorizedView categorized rendering flow", caseCategorizedView);

    std::printf("checks run: %d\n", gChecks);
    std::printf("TEST SUMMARY: %d passed, %d failed\n",
                gCasesPassed, gCases - gCasesPassed);
    return gCasesPassed == gCases ? 0 : 1;
}
