#include <QCoreApplication>
#include <QString>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);
    const QString value = QStringLiteral("libngf-qt");
    if (value != QStringLiteral("libngf-qt"))
        return 1;
    std::printf("libngf-qt test PASSED\n");
    return 0;
}
