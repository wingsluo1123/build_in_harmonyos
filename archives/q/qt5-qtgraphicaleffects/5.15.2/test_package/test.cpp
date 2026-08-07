#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QString>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);
    // QtGraphicalEffects 是 QML 模块（无 C++ 链接库）。
    // QML 模块目录由 test_package/conanfile.py 通过 CMake 编译定义
    // QML_MODULE_DIR 传入（指向被测包内的 qml/ 目录），确保测试真实
    // 校验被测包产物，且不依赖 applicationDirPath() 相对路径。
#ifdef QML_MODULE_DIR
    const QString qmlDir = QStringLiteral(QML_MODULE_DIR);
#else
    const QString qmlDir = QStringLiteral("");
#endif
    if (qmlDir.isEmpty() || !QFileInfo::exists(qmlDir + QStringLiteral("/QtGraphicalEffects/qmldir"))) {
        std::printf("Qt5GraphicalEffects test FAILED: qmldir not found in %s\n",
                    qmlDir.toUtf8().constData());
        return 1;
    }
    std::printf("Qt5GraphicalEffects test PASSED\n");
    return 0;
}
