// kxmlgui 6.28.0 consumer test: a small executor that drives the public
// KXmlGuiWindow API end to end. Each case is reported independently as
// TEST PASS / TEST FAIL; the process exits 1 if any case fails.
#include <KActionCategory>
#include <KActionCollection>
#include <KConfigGroup>
#include <KToolBar>
#include <KXmlGuiWindow>

#include <QAction>
#include <QApplication>
#include <QString>

#include <cstdio>

namespace
{
int g_passed = 0;
int g_failed = 0;

void report(const char *name, bool ok, const QString &detail = QString())
{
    if (ok) {
        ++g_passed;
        std::printf("TEST PASS: %s\n", name);
    } else {
        ++g_failed;
        std::printf("TEST FAIL: %s", name);
        if (!detail.isEmpty()) {
            std::printf(" (%s)", detail.toUtf8().constData());
        }
        std::printf("\n");
    }
}

void caseWindowTitle()
{
    KXmlGuiWindow win;
    win.setWindowTitle(QStringLiteral("kxmlgui-consumer"));
    report("window_construct_title",
           win.windowTitle() == QStringLiteral("kxmlgui-consumer"),
           win.windowTitle());
}

void caseActionCollection()
{
    KXmlGuiWindow win;
    KActionCollection *collection = win.actionCollection();
    if (!collection) {
        report("action_collection_add_lookup", false, QStringLiteral("null actionCollection"));
        return;
    }
    QAction *added = collection->addAction(QStringLiteral("consumer_action"), new QAction(&win));
    QAction *lookedUp = collection->action(QStringLiteral("consumer_action"));
    report("action_collection_add_lookup",
           added != nullptr && lookedUp == added && collection->count() >= 1,
           QStringLiteral("count=%1").arg(collection->count()));
}

void caseActionCategory()
{
    KXmlGuiWindow win;
    KActionCollection *collection = win.actionCollection();
    if (!collection) {
        report("action_category_registration", false, QStringLiteral("null actionCollection"));
        return;
    }
    KActionCategory category(QStringLiteral("ConsumerCategory"), collection);
    QAction *action = category.addAction(QStringLiteral("categorized_action"), new QAction(&win));
    report("action_category_registration",
           action != nullptr
               && collection->action(QStringLiteral("categorized_action")) == action,
           QStringLiteral("count=%1").arg(collection->count()));
}

void caseCreateGui()
{
    KXmlGuiWindow win;
    win.createGUI();
    report("create_gui_factory", win.guiFactory() != nullptr);
}

void caseToolBar()
{
    KXmlGuiWindow win;
    KToolBar *bar = win.toolBar();
    report("main_toolbar_autocreate",
           bar != nullptr && !win.toolBars().isEmpty(),
           QStringLiteral("toolbars=%1").arg(win.toolBars().size()));
}

void caseAutoSaveSettings()
{
    KXmlGuiWindow win;
    win.setAutoSaveSettings(QStringLiteral("kxmlgui-consumer-test"));
    KConfigGroup group = win.autoSaveConfigGroup();
    report("autosave_settings_group",
           group.isValid() && group.name() == QStringLiteral("kxmlgui-consumer-test"),
           group.name());
}
} // namespace

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    caseWindowTitle();
    caseActionCollection();
    caseActionCategory();
    caseCreateGui();
    caseToolBar();
    caseAutoSaveSettings();

    std::printf("TEST SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
