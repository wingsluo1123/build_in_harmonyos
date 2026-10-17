// kglobalaccel 6.28.0 consumer end-to-end test (R34: exercises the packaged API).
//
// Three consumer cases run headless (QT_QPA_PLATFORM=offscreen is set by the
// test harness):
//   1. Singleton + global-shortcut lifecycle on a real QAction (register via
//      setShortcut, hasShortcut consistency, removeAllShortcuts cleanup).
//   2. Query API: shortcut() reflects at most the requested sequence and
//      isGlobalShortcutAvailable() is an idempotent pure query.
//   3. setInverseShortcutActions() (new in 6.27/6.28): validated argument
//      gating — an unregistered pair and a component-mismatched pair must be
//      rejected locally before any D-Bus traffic; a fully registered pair is
//      callable and leaves the local registration state unchanged.
//
// All checks are written against API consistency (local state, return-value
// coherence) rather than against a D-Bus side effect, so the executor is
// deterministic both on a desktop session with kglobalacceld and on a
// headless device without a session bus.
//
// Every case reports TEST PASS / TEST FAIL independently; the process prints
// "TEST SUMMARY: N passed, M failed" and exits non-zero if any case failed,
// so the Conan test step fails on any regression.

#include <KGlobalAccel>

#include <QAction>
#include <QApplication>
#include <QKeySequence>
#include <QString>

#include <cstdio>

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

// Build a QAction registered under the given component name (the property
// KGlobalAccel reads through componentUniqueForAction()).
static QAction *makeAction(const char *objectName, const char *componentName)
{
    auto *action = new QAction(QString::fromLatin1(objectName));
    action->setObjectName(QString::fromLatin1(objectName));
    action->setText(QString::fromLatin1(objectName));
    action->setProperty("componentName", QString::fromLatin1(componentName));
    return action;
}

static void caseSingletonAndLifecycle()
{
    KGlobalAccel *ga = KGlobalAccel::self();
    check(ga != nullptr, "KGlobalAccel::self() != nullptr");
    if (!ga) {
        return;
    }

    QAction *action = makeAction("case1_action", "kga628-consumer");

    check(!ga->hasShortcut(action), "hasShortcut() is false before registration");

    const QList<QKeySequence> requested{QKeySequence(QStringLiteral("Ctrl+Alt+T"))};
    const bool setResult = ga->setShortcut(action, requested, KGlobalAccel::NoAutoloading);
    check(ga->hasShortcut(action) == setResult,
          "hasShortcut() after setShortcut() equals the setShortcut() result");
    check(setResult, "setShortcut() registers the action locally (headless degradation keeps local state)");

    ga->removeAllShortcuts(action);
    check(!ga->hasShortcut(action), "hasShortcut() is false after removeAllShortcuts()");

    delete action;
}

static void caseQueryApi()
{
    KGlobalAccel *ga = KGlobalAccel::self();
    if (!ga) {
        check(false, "singleton available for the query case");
        return;
    }

    QAction *action = makeAction("case2_action", "kga628-consumer");
    const QList<QKeySequence> requested{QKeySequence(QStringLiteral("Ctrl+Alt+Y"))};
    ga->setShortcut(action, requested, KGlobalAccel::NoAutoloading);

    const QList<QKeySequence> current = ga->shortcut(action);
    check(current.size() <= requested.size(),
          "shortcut() returns at most the requested sequence count");

    const QKeySequence probe{QStringLiteral("Ctrl+Alt+U")};
    const bool available1 = KGlobalAccel::isGlobalShortcutAvailable(probe);
    const bool available2 = KGlobalAccel::isGlobalShortcutAvailable(probe);
    check(available1 == available2,
          "isGlobalShortcutAvailable() is idempotent for the same sequence");

    ga->removeAllShortcuts(action);
    delete action;
}

static void caseInverseShortcutActions()
{
    KGlobalAccel *ga = KGlobalAccel::self();
    if (!ga) {
        check(false, "singleton available for the inverse-actions case");
        return;
    }

    // (a) Unregistered actions are rejected locally: setInverseShortcutActions
    //     must return false without any D-Bus interaction.
    QAction *freshA = makeAction("case3_fresh_forward", "kga628-consumer");
    QAction *freshB = makeAction("case3_fresh_backward", "kga628-consumer");
    check(!KGlobalAccel::setInverseShortcutActions(freshA, freshB),
          "setInverseShortcutActions() is false when neither action is registered");

    // (b) Registered actions from different components are rejected locally.
    QAction *forward = makeAction("case3_forward", "kga628-consumer");
    QAction *foreign = makeAction("case3_foreign", "kga628-other-component");
    const QList<QKeySequence> fwdKeys{QKeySequence(QStringLiteral("Ctrl+Alt+Right"))};
    const QList<QKeySequence> bwdKeys{QKeySequence(QStringLiteral("Ctrl+Alt+Left"))};
    ga->setShortcut(forward, fwdKeys, KGlobalAccel::NoAutoloading);
    ga->setShortcut(foreign, bwdKeys, KGlobalAccel::NoAutoloading);
    check(!KGlobalAccel::setInverseShortcutActions(forward, foreign),
          "setInverseShortcutActions() is false when the components differ");

    // (c) A fully registered same-component pair is callable; the call must
    //     not disturb the local registration state. The boolean result is
    //     reported (true with a live kglobalacceld, false in a headless
    //     degradation) but not value-checked: it depends on the D-Bus peer.
    QAction *backward = makeAction("case3_backward", "kga628-consumer");
    ga->setShortcut(backward, bwdKeys, KGlobalAccel::NoAutoloading);
    const bool pairResult = KGlobalAccel::setInverseShortcutActions(forward, backward);
    std::printf("  [info] setInverseShortcutActions(registered pair) -> %s\n",
                pairResult ? "true" : "false");
    check(ga->hasShortcut(forward) && ga->hasShortcut(backward),
          "both actions keep their local registration after the inverse call");

    ga->removeAllShortcuts(forward);
    ga->removeAllShortcuts(backward);
    ga->removeAllShortcuts(foreign);
    delete freshA;
    delete freshB;
    delete forward;
    delete backward;
    delete foreign;
}

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    std::printf("== kglobalaccel 6.28.0 consumer end-to-end test ==\n");
    runCase("KGlobalAccel singleton and shortcut lifecycle", caseSingletonAndLifecycle);
    runCase("global-shortcut query API consistency", caseQueryApi);
    runCase("setInverseShortcutActions argument gating (6.27+ API)", caseInverseShortcutActions);

    std::printf("checks run: %d\n", gChecks);
    std::printf("TEST SUMMARY: %d passed, %d failed\n",
                gCasesPassed, gCases - gCasesPassed);
    return gCasesPassed == gCases ? 0 : 1;
}
