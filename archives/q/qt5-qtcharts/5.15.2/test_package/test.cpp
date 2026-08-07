#include <QCoreApplication>
#include <QString>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);
    const QString value = QStringLiteral("qt5-qtcharts");
    if (value != QStringLiteral("qt5-qtcharts"))
        return 1;
    std::printf("Qt5Charts test PASSED\n");
    return 0;
}
