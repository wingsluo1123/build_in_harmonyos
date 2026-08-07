#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);
    // QtGraphicalEffects 是 QML 模块（无 C++ 链接库），
    // 验证包内 QML 模块目录（qmldir）确实随包发布
    const QString prefix = QCoreApplication::applicationDirPath();
    QDir base(prefix);
    QString qmlDir;
    if (base.exists(QStringLiteral("../qml/QtGraphicalEffects/qmldir"))) {
        qmlDir = base.absoluteFilePath(QStringLiteral("../qml/QtGraphicalEffects"));
    } else if (base.exists(QStringLiteral("qml/QtGraphicalEffects/qmldir"))) {
        qmlDir = base.absoluteFilePath(QStringLiteral("qml/QtGraphicalEffects"));
    }
    if (qmlDir.isEmpty() || !QFileInfo::exists(qmlDir + QStringLiteral("/qmldir"))) {
        std::printf("Qt5GraphicalEffects test FAILED: qmldir not found\n");
        return 1;
    }
    std::printf("Qt5GraphicalEffects test PASSED\n");
    return 0;
}
