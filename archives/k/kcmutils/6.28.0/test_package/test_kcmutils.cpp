// kcmutils 6.28.0 consumer end-to-end test (R34: real API, real workflow).
//
// The test acts as a system-settings consumer (kinfocenter / systemsettings):
// it builds its own KCM plugin in this package, loads it through
// KCModuleLoader, embeds it as a KCMultiDialog page, drives the error
// fallback path for an unknown module, and queries KCModuleData through
// KF6::KCMUtilsCore.
//
// Executor contract: every case prints "TEST PASS <name>" or
// "TEST FAIL <name>: <reason>"; the summary line is
// "E2E TEST SUMMARY: N passed, M failed"; any failure exits with status 1.
#include <KCModule>
#include <KCModuleData>
#include <KCModuleLoader>
#include <KCMultiDialog>
#include <KPluginMetaData>

#include <QApplication>

#include <cstdio>

static int g_passed = 0;
static int g_failed = 0;

static void check(const char *name, bool ok, const char *reason = "")
{
    if (ok) {
        ++g_passed;
        std::printf("TEST PASS %s\n", name);
    } else {
        ++g_failed;
        std::printf("TEST FAIL %s: %s\n", name, reason);
    }
    std::fflush(stdout);
}

int main(int argc, char **argv)
{
    QApplication app(argc, argv);
    if (argc < 2) {
        std::printf("TEST FAIL plugin_path: consumer_kcm plugin path argument missing\n");
        std::printf("E2E TEST SUMMARY: 0 passed, 1 failed\n");
        return 1;
    }
    const QString pluginPath = QString::fromLocal8Bit(argv[1]);

    // Case 1: the consumer builds and loads its own KCM plugin.
    const KPluginMetaData meta(pluginPath);
    check("plugin_metadata", meta.isValid(), "KPluginMetaData could not read the consumer plugin");

    KCModule *module = KCModuleLoader::loadModule(meta);
    check("module_load", module != nullptr, "KCModuleLoader returned null");
    if (module) {
        check("module_class",
              qstrcmp(module->metaObject()->className(), "KCMError") != 0,
              "loader fell back to KCMError for a valid plugin");
        module->load();
        check("module_widget", module->widget() != nullptr, "KCModule::widget() returned null");
    }

    // Case 2: the consumer embeds the module as a KCMultiDialog page.
    KCMultiDialog dialog;
    KPageWidgetItem *item = dialog.addModule(meta);
    check("dialog_add_module", item != nullptr, "KCMultiDialog::addModule returned null");
    check("dialog_no_error", !dialog.hasError(), "KCMultiDialog reports an error for a valid module");

    // Case 3: an unknown module takes the real loader error path.
    KCModule *broken = KCModuleLoader::loadModule(KPluginMetaData(QStringLiteral("nonexistent_kcm")));
    check("unknown_module_fallback",
          broken != nullptr && qstrcmp(broken->metaObject()->className(), "KCMError") == 0,
          "unknown module did not produce the KCMError fallback");

    // Case 4: KCMUtilsCore data model (default relevance of an empty KCM).
    KCModuleData data;
    check("module_data_relevance", data.isRelevant(), "default KCModuleData claims irrelevance");

    std::printf("E2E TEST SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
