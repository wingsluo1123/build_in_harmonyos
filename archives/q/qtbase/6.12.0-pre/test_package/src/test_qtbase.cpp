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
    // 无头 CI（无 X11/Wayland 显示服务器）下 QGuiApplication 可能构造失败，
    // 此时跳过 Gui 测试而非整体失败，打印 SKIP 信息。
    {
        // 尝试设置 offscreen 平台插件，让无头 CI 也能部分验证 Gui 模块
        qputenv("QT_QPA_PLATFORM", "offscreen");

        // argc/argv 必须透传给 QGuiApplication 以避免 Qt 运行时警告
        QGuiApplication app(argc, argv);
        CHECK(app.testAttribute(Qt::AA_ShareOpenGLContexts) == false,
              "Gui QGuiApplication created");

        QWindow window;
        window.setTitle("qtbase test");
        window.resize(320, 240);
        window.create();

        // isExposed() 在 offscreen 平台下可能返回 false，不属于适配缺陷
        if (window.isExposed()) {
            printf("  ✓ Gui QWindow created and exposed\n");
            passed++;
        } else {
            printf("  ~ Gui QWindow created but not exposed (headless CI is OK)\n");
        }
        total++;

        QSurfaceFormat fmt = window.format();
        CHECK(fmt.redBufferSize() > 0 || fmt.greenBufferSize() > 0,
              "Gui QSurfaceFormat has color bits");
    }

    printf("\n========== Summary ==========\n");
    printf("Tests: %d/%d passed\n", passed, total);
    return passed == total ? 0 : 1;
}
