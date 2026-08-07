#include <QCoreApplication>
#include <QString>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);
    const QString value = QStringLiteral("qt5-qt3d");
    if (value != QStringLiteral("qt5-qt3d"))
        return 1;
    std::printf("Qt53D test PASSED\n");
    return 0;
}
