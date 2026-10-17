#include <Config.h>
#include <EpisodeAction.h>
#include <QCoreApplication>
#include <QVariantMap>
#include <cstdio>
#include <cstdlib>

static int passed = 0;
static void check(bool ok, const char *name) {
    if (!ok) { std::fprintf(stderr, "FAIL: %s\n", name); std::exit(1); }
    ++passed; std::printf("PASS: %s\n", name);
}
int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    mygpo::Config *cfg = mygpo::Config::instance();
    check(cfg->majorVersion()==1 && cfg->minorVersion()==1 && cfg->patchVersion()==0 && cfg->version()==QStringLiteral("1.1.0"), "installed version");
    const QUrl original = cfg->mygpoBaseUrl();
    cfg->setMygpoBaseUrl(QUrl(QStringLiteral("https://podcasts.example.org/base/")));
    check(cfg->mygpoBaseUrl()==QUrl(QStringLiteral("https://podcasts.example.org/base/")), "endpoint override");
    cfg->setMygpoBaseUrl(original);
    cfg->setUserAgentPrefix(QStringLiteral("HarmonyOS-test"));
    check(cfg->userAgent()==QStringLiteral("HarmonyOS-test libmygpo-qt 1.1.0"), "user agent composition");
    mygpo::EpisodeAction action(QUrl(QStringLiteral("https://example.org/feed")), QUrl(QStringLiteral("https://example.org/episode")), QStringLiteral("harmony"), mygpo::EpisodeAction::Play, 1234, 10, 40, 100);
    check(action.action()==mygpo::EpisodeAction::Play && action.timestamp()==1234 && action.started()==10 && action.position()==40 && action.total()==100, "playback action data");
    check(action.podcastUrl()==QUrl(QStringLiteral("https://example.org/feed")) && action.episodeUrl()==QUrl(QStringLiteral("https://example.org/episode")) && action.deviceName()==QStringLiteral("harmony"), "podcast and device identity");
    check(action.property("position").toULongLong()==40 && action.metaObject()->indexOfProperty("action")>=0, "exported Qt metaobject");
    std::printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"consumer_total\":6,\"consumer_passed\":%d}\n", passed);
    return 0;
}
