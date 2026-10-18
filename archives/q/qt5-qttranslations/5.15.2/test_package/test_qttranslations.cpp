// 消费者视角验证：用 Qt5 运行时（QTranslator）真实加载本包打包产出的
// translations/*.qm，证明 Qt5 应用能消费该翻译资源包。
#include <QDir>
#include <QFileInfo>
#include <QString>
#include <QStringList>
#include <QTranslator>

#include <cstdio>
#include <cstdlib>

static int g_failures = 0;

static void check(bool condition, const char *message) {
    std::printf("%s %s\n", condition ? "[PASS]" : "[FAIL]", message);
    if (!condition) {
        ++g_failures;
    }
}

int main() {
    const char *env = std::getenv("QT_TRANSLATIONS_PATH");
    check(env != nullptr && env[0] != '\0', "QT_TRANSLATIONS_PATH is set");
    if (env == nullptr || env[0] == '\0') {
        return 1;
    }

    const QDir dir(QString::fromLocal8Bit(env));
    check(dir.exists(), "QT_TRANSLATIONS_PATH directory exists");

    const QStringList qms = dir.entryList(QStringList() << "*.qm", QDir::Files);
    std::printf("[info] packaged .qm count = %d\n", static_cast<int>(qms.size()));
    check(qms.size() >= 250, ">= 250 .qm translation files packaged");

    // 关键中文翻译：既要落位，又要能被 Qt5 运行时 QTranslator 真正加载
    const char *keys[] = {
        "qt_zh_CN",
        "assistant_zh_CN",
        "designer_zh_CN",
        "linguist_zh_CN",
        "qt_help_zh_CN",
    };
    for (const char *key : keys) {
        const QString name = QString::fromLatin1(key);
        const QString path = dir.filePath(name + QStringLiteral(".qm"));
        check(QFileInfo::exists(path), (QStringLiteral("present: ") + name + QStringLiteral(".qm")).toUtf8().constData());

        QTranslator translator;
        const bool loaded = translator.load(path);
        check(loaded && !translator.isEmpty(),
              (QStringLiteral("Qt5 QTranslator loads non-empty: ") + name + QStringLiteral(".qm")).toUtf8().constData());
    }

    std::printf("[info] failures = %d\n", g_failures);
    return g_failures == 0 ? 0 : 1;
}
