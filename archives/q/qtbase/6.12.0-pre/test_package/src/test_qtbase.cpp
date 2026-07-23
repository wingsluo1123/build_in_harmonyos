// R34: 实质调用 Qt6::Core API 验证链通
#include <QString>
#include <QDebug>
#include <cstdio>

int main() {
    QString s = QStringLiteral("hello qt6");
    qDebug() << s;
    printf("qtbase Core link OK: %s\n", qPrintable(s));
    return 0;
}
