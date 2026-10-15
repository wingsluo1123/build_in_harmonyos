// test_qt_advanced_docking_system.cpp
//
// Consumer-side test for the packaged Qt Advanced Docking System (QtADS) 4.5.0.
//
// It links the exported target `ads::qtadvanceddocking-qt6` and exercises the
// real public API (R34): dock manager lifecycle, docking into all four areas,
// the dock-widget registry, view toggling, perspectives, the floating dock
// container path and a saveState/restoreState round trip.
//
// The whole test runs headless through Qt's offscreen QPA plugin
// (QT_QPA_PLATFORM=offscreen), which is how the other GUI packages in this
// repository are verified on OHOS (no X11/Wayland display).

#include <QApplication>
#include <QByteArray>
#include <QLabel>
#include <QMainWindow>
#include <QStringList>
#include <QTextEdit>

#include <cstdio>

#include <DockAreaWidget.h>
#include <DockManager.h>
#include <DockWidget.h>
#include <FloatingDockContainer.h>

static int g_checks = 0;
static int g_failures = 0;

static void check(bool condition, const char *what, int line)
{
    ++g_checks;
    if (condition)
    {
        std::printf("ok   %s\n", what);
    }
    else
    {
        ++g_failures;
        std::printf("FAIL %s (line %d)\n", what, line);
    }
}

#define CHECK(cond) check((cond), #cond, __LINE__)

static ads::CDockWidget *makeDockWidget(ads::CDockManager *manager,
                                        const QString &title,
                                        const QString &text)
{
    ads::CDockWidget *dockWidget = new ads::CDockWidget(manager, title);
    dockWidget->setWidget(new QLabel(text));
    return dockWidget;
}

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);

    // --- configuration flags (static, must be set before the manager) -------
    ads::CDockManager::setConfigFlag(ads::CDockManager::OpaqueSplitterResize, true);
    ads::CDockManager::setConfigFlag(ads::CDockManager::FocusHighlighting, true);
    ads::CDockManager::setConfigFlag(ads::CDockManager::DockAreaHasCloseButton, true);
    CHECK(ads::CDockManager::testConfigFlag(ads::CDockManager::OpaqueSplitterResize));
    CHECK(ads::CDockManager::testConfigFlag(ads::CDockManager::FocusHighlighting));

    // --- dock manager -------------------------------------------------------
    QMainWindow window;
    ads::CDockManager *manager = new ads::CDockManager(&window);
    CHECK(manager != nullptr);
    window.setCentralWidget(manager);
    window.resize(1024, 768);
    window.show();
    CHECK(manager->dockWidgetsMap().isEmpty());

    // --- dock widgets in the four dock areas --------------------------------
    ads::CDockWidget *left = makeDockWidget(manager, "LeftDock", "left content");
    ads::CDockWidget *right = makeDockWidget(manager, "RightDock", "right content");
    ads::CDockWidget *top = makeDockWidget(manager, "TopDock", "top content");
    ads::CDockWidget *bottom = makeDockWidget(manager, "BottomDock", "bottom content");

    CHECK(manager->addDockWidget(ads::LeftDockWidgetArea, left) != nullptr);
    CHECK(manager->addDockWidget(ads::RightDockWidgetArea, right) != nullptr);
    CHECK(manager->addDockWidget(ads::TopDockWidgetArea, top) != nullptr);
    CHECK(manager->addDockWidget(ads::BottomDockWidgetArea, bottom) != nullptr);

    CHECK(manager->dockWidgetsMap().size() == 4);
    CHECK(manager->dockWidgetsMap().contains("LeftDock"));
    CHECK(manager->dockWidgetsMap().value("LeftDock") == left);
    CHECK(left->dockAreaWidget() != nullptr);
    CHECK(right->dockAreaWidget() != nullptr);
    CHECK(!left->isClosed());
    CHECK(!right->isClosed());
    CHECK(!left->isFloating());

    // --- tabified dock area: addDockWidgetTab creates its own dock area -------
    ads::CDockWidget *tabbed = makeDockWidget(manager, "TabbedDock", "tabbed content");
    CHECK(manager->addDockWidgetTab(ads::CenterDockWidgetArea, tabbed) != nullptr);
    CHECK(tabbed->dockAreaWidget() != nullptr);
    // It is a *new* dock area: the Center area is distinct from the Left area
    // that holds `left` (asserting inequality, not a tautology).
    CHECK(tabbed->dockAreaWidget() != left->dockAreaWidget());

    // --- view toggle (close/open) -------------------------------------------
    left->toggleView(false);
    CHECK(left->isClosed());
    left->toggleView(true);
    CHECK(!left->isClosed());

    // --- perspectives -------------------------------------------------------
    manager->addPerspective("LayoutOne");
    CHECK(manager->perspectiveNames().contains("LayoutOne"));
    CHECK(manager->perspectiveNames().size() >= 1);

    // --- save/restore round trip -------------------------------------------
    const QByteArray state = manager->saveState();
    CHECK(!state.isEmpty());
    CHECK(manager->restoreState(state));

    // --- floating dock container -------------------------------------------
    ads::CDockWidget *floating = makeDockWidget(manager, "FloatingDock", "floating content");
    ads::CFloatingDockContainer *floatingContainer =
        manager->addDockWidgetFloating(floating);
    CHECK(floatingContainer != nullptr);
    CHECK(floating->isFloating());
    CHECK(!manager->floatingWidgets().isEmpty());

    // Docking it back must clear the floating state.
    CHECK(manager->addDockWidget(ads::CenterDockWidgetArea, floating) != nullptr);
    CHECK(!floating->isFloating());

    std::printf("\n%d checks, %d failures\n", g_checks, g_failures);
    if (g_failures != 0)
    {
        std::printf("RESULT: FAILED\n");
        return 1;
    }
    std::printf("RESULT: PASSED\n");
    return 0;
}
