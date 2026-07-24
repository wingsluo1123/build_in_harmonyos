// R34: 实质调用 Qt6 API 验证链通 — 覆盖 Core + Network + Xml + Concurrent + Gui
#include <QString>
#include <QDebug>
#include <QByteArray>
#include <QDateTime>
#include <QList>
#include <QRegularExpression>
#include <QTcpServer>
#include <QXmlStreamReader>
#include <QtConcurrent>
#include <QGuiApplication>
#include <QWindow>
#include <QSurfaceFormat>
#include <cstdio>

#define CHECK(cond, msg) do { \
    total++; \
    if (!(cond)) { \
        printf("  ✗ %s (FAILED)\n", msg); \
        return 1; \
    } \
    printf("  ✓ %s\n", msg); \
    passed++; \
} while(0)

// 简单并行函数（QConcurrent 验证）
static QString concurrentTest() {
    return QStringLiteral("concurrent ok");
}

int main(int argc, char *argv[]) {
    int passed = 0, total = 0;

    // ── Core: QStringLiteral + qDebug ──
    {
        QString s = QStringLiteral("hello qt6");
        qDebug() << s;
        CHECK(!s.isEmpty(), "Core QStringLiteral + qDebug");
        printf("  [Core] %s\n", qPrintable(s));
    }

    // ── Core: QDateTime ──
    {
        QDateTime now = QDateTime::currentDateTime();
        CHECK(now.isValid(), "Core QDateTime currentDateTime");
        printf("  [Core] %s\n", qPrintable(now.toString(Qt::ISODate)));
    }

    // ── Core: QRegularExpression ──
    {
        QRegularExpression re("qt\\d+");
        CHECK(re.isValid(), "Core QRegularExpression valid");
    }

    // ── Network: QTcpServer ──
    {
        QTcpServer server;
        CHECK(server.listen(QHostAddress::LocalHost), "Network QTcpServer listen");
        printf("  [Network] port %d\n", server.serverPort());
        server.close();
    }

    // ── Xml: QXmlStreamReader ──
    {
        QByteArray xmlData = "<root><item id=\"1\">test</item></root>";
        QXmlStreamReader xml(xmlData);
        bool foundRoot = false;
        while (!xml.atEnd() && !xml.hasError()) {
            xml.readNext();
            if (xml.isStartElement() && xml.name().toString() == "root")
                foundRoot = true;
        }
        CHECK(foundRoot, "Xml QXmlStreamReader parse");
    }

    // ── Concurrent: QtConcurrent::run ──
    {
        QFuture<QString> future = QtConcurrent::run(concurrentTest);
        future.waitForFinished();
        CHECK(future.result() == "concurrent ok", "Concurrent QtConcurrent::run");
    }

    // ── Gui: QGuiApplication + QWindow（R40 图形栈验证）──
    {
        // QGuiApplication 仅创建一次，透传 argc/argv 避免 Qt 警告
        QGuiApplication app(argc, argv);
        CHECK(app.testAttribute(Qt::AA_ShareOpenGLContexts) == false,
              "Gui QGuiApplication created");

        QWindow window;
        window.setTitle("qtbase test");
        window.resize(320, 240);
        window.create();
        CHECK(window.isExposed(), "Gui QWindow created and exposed");

        QSurfaceFormat fmt = window.format();
        CHECK(fmt.redBufferSize() > 0 || fmt.greenBufferSize() > 0,
              "Gui QSurfaceFormat has color bits");
    }

    printf("\n========== Summary ==========\n");
    printf("Tests: %d/%d passed\n", passed, total);
    return passed == total ? 0 : 1;
}
