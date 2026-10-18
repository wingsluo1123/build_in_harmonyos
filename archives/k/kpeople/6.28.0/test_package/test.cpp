// Consumer executor for the kpeople HarmonyOS PC adaptation.
//
// Drives the public consumer surface of the packaged KF6People stack on the
// real device: the KPeople core model API (PersonsModel /
// PersonsSortFilterProxyModel / PersonData), the KF6PeopleBackend and
// KF6PeopleWidgets linkage, and the packaged vCard data source plugin
// discovered through the Qt plugin path, exactly like a real person-centric
// application would.
//
// Every case prints its own "TEST PASS"/"TEST FAIL" line and the run ends
// with a TEST SUMMARY line; any failed case makes the process exit(1).
#include <KPeople/PersonData>
#include <KPeople/PersonPluginManager>
#include <KPeople/PersonsModel>
#include <KPeople/PersonsSortFilterProxyModel>
#include <KPeopleBackend/BasePersonsDataSource>
#include <KPeople/Widgets/PersonDetailsView>

#include <QCoreApplication>
#include <QString>
#include <cstdio>
#include <cstring>
#include <string>

namespace {

int g_passed = 0;
int g_failed = 0;

void report(bool ok, const char *name, const std::string &detail)
{
    if (ok) {
        ++g_passed;
        std::printf("TEST PASS: %s\n", name);
    } else {
        ++g_failed;
        std::printf("TEST FAIL: %s (%s)\n", name, detail.c_str());
    }
    std::fflush(stdout);
}

} // namespace

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    app.setApplicationName(QStringLiteral("test_kpeople"));

    // Case 1: core model API on the fresh, empty person database.
    KPeople::PersonsModel model;
    report(model.rowCount() == 0,
           "persons_model_empty",
           "expected empty persons model, got " + std::to_string(model.rowCount()) + " rows");

    // Case 2: the sorting/filtering proxy accepts the model as source.
    KPeople::PersonsSortFilterProxyModel proxy;
    proxy.setSourceModel(&model);
    report(proxy.rowCount() == 0,
           "persons_sort_filter_proxy_empty",
           "expected empty proxy model, got " + std::to_string(proxy.rowCount()) + " rows");

    // Case 3: PersonData against the empty store stays invalid without crashing.
    KPeople::PersonData missing(QStringLiteral("fakesource://contact1"));
    report(!missing.isValid() && missing.name().isEmpty(),
           "person_data_unknown_invalid",
           "unknown person unexpectedly reports valid or named");

    // Case 4: the KF6PeopleBackend and KF6PeopleWidgets libraries are live.
    report(std::strcmp(KPeople::BasePersonsDataSource::staticMetaObject.className(),
                       "KPeople::BasePersonsDataSource") == 0,
           "backend_metaobject_available",
           "KPeople::BasePersonsDataSource metaobject unavailable at runtime");
    report(std::strcmp(KPeople::PersonDetailsView::staticMetaObject.className(),
                       "KPeople::PersonDetailsView") == 0,
           "widgets_metaobject_available",
           "KPeople::PersonDetailsView metaobject unavailable at runtime");

    // Case 5: the packaged vCard data source plugin is discovered through the
    // Qt plugin path (kpeople/datasource plugin namespace).
    bool vcardFound = false;
    const QList<KPeople::BasePersonsDataSource *> sources = KPeople::PersonPluginManager::dataSourcePlugins();
    for (const KPeople::BasePersonsDataSource *source : sources) {
        if (source->sourcePluginId() == QStringLiteral("vcard")) {
            vcardFound = true;
        }
    }
    report(vcardFound,
           "vcard_datasource_discovered",
           "vCard datasource missing from plugin list (" + std::to_string(sources.size())
               + " datasource(s))");

    std::printf("TEST SUMMARY: %d/%d passed\n", g_passed, g_passed + g_failed);
    return g_failed == 0 ? 0 : 1;
}
