// test_libquotient.cpp -- consumer-side API test for the installed
// libQuotient 0.8.0 (Qt6) package.
//
// The upstream library exposes a large surface; this program exercises the
// central objects a consumer touches first -- Connection (the homeserver
// property) and RoomMessageEvent (JSON parsing, construction, fullJson()
// round trip, and the loadEvent() dispatch used by sync processing).
// Nothing here needs a network or a homeserver; the harness sets
// QT_QPA_PLATFORM=offscreen for uniformity with the other Qt test packages.
//
// Output protocol (house rule12): one "TEST PASS/FAIL <case>" line per case
// and a final "TEST SUMMARY"; the process exits 1 if any case failed.
#include <Quotient/connection.h>
#include <Quotient/events/event.h>
#include <Quotient/events/roommessageevent.h>

#include <QtCore/QCoreApplication>
#include <QtCore/QJsonObject>
#include <QtCore/QUrl>

#include <functional>
#include <iostream>

static int g_failed = 0;
static int g_assertions = 0;

#define CHECK(condition)                                              \
    do {                                                              \
        ++g_assertions;                                               \
        if (!(condition)) {                                           \
            ++g_failed;                                               \
            std::cout << "  ASSERT FAILED: " #condition << std::endl; \
        }                                                             \
    } while (false)

static void runCase(const char* name, const std::function<void()>& body)
{
    std::cout << "TEST " << name << std::endl;
    const int failedBefore = g_failed;
    body();
    if (g_failed == failedBefore)
        std::cout << "TEST PASS " << name << std::endl;
    else
        std::cout << "TEST FAIL " << name << std::endl;
}

static QJsonObject messageJson(const QString& msgtype, const QString& body)
{
    return QJsonObject{
        { QStringLiteral("type"), QStringLiteral("m.room.message") },
        { QStringLiteral("event_id"), QStringLiteral("$event0") },
        { QStringLiteral("sender"), QStringLiteral("@alice:example.org") },
        { QStringLiteral("content"),
          QJsonObject{ { QStringLiteral("msgtype"), msgtype },
                       { QStringLiteral("body"), body } } },
    };
}

int main(int argc, char* argv[])
{
    QCoreApplication app(argc, argv);
    Q_UNUSED(app)

    runCase("connection_homeserver_roundtrip", [] {
        Quotient::Connection connection;
        CHECK(connection.homeserver().isEmpty());
        const QUrl server(QStringLiteral("https://matrix.example.org"));
        connection.setHomeserver(server);
        CHECK(connection.homeserver() == server);
    });

    runCase("roommessageevent_parse_json", [] {
        const Quotient::RoomMessageEvent event(
            messageJson(QStringLiteral("m.text"), QStringLiteral("hello harmony")));
        CHECK(event.rawMsgtype() == QStringLiteral("m.text"));
        CHECK(event.plainBody() == QStringLiteral("hello harmony"));
        CHECK(event.msgtype() == Quotient::RoomMessageEvent::MsgType::Text);
    });

    runCase("roommessageevent_parse_non_text_msgtype", [] {
        const Quotient::RoomMessageEvent event(
            messageJson(QStringLiteral("m.emote"), QStringLiteral("* waves")));
        CHECK(event.rawMsgtype() == QStringLiteral("m.emote"));
        CHECK(event.plainBody() == QStringLiteral("* waves"));
        CHECK(event.msgtype() != Quotient::RoomMessageEvent::MsgType::Text);
    });

    runCase("roommessageevent_construct_plaintext", [] {
        const Quotient::RoomMessageEvent event(QStringLiteral("plain harmony"));
        CHECK(event.plainBody() == QStringLiteral("plain harmony"));
        CHECK(event.rawMsgtype() == QStringLiteral("m.text"));
    });

    runCase("roommessageevent_fulljson_fields", [] {
        const Quotient::RoomMessageEvent event(
            messageJson(QStringLiteral("m.notice"), QStringLiteral("round trip")));
        const QJsonObject json = event.fullJson();
        CHECK(json[QStringLiteral("type")].toString()
              == QStringLiteral("m.room.message"));
        CHECK(json[QStringLiteral("sender")].toString()
              == QStringLiteral("@alice:example.org"));
        CHECK(json[QStringLiteral("content")].toObject()[QStringLiteral("body")].toString()
              == QStringLiteral("round trip"));
    });

    runCase("load_event_dispatch", [] {
        const auto event = Quotient::loadEvent<Quotient::RoomMessageEvent>(
            messageJson(QStringLiteral("m.notice"), QStringLiteral("notice body")));
        CHECK(event != nullptr);
        if (event) {
            CHECK(event->rawMsgtype() == QStringLiteral("m.notice"));
            CHECK(event->plainBody() == QStringLiteral("notice body"));
        }
    });

    std::cout << "TEST SUMMARY: " << g_assertions << " assertion(s), " << g_failed
              << " failure(s)" << std::endl;
    return g_failed == 0 ? 0 : 1;
}
