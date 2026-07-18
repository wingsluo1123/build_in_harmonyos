#include <QColor>
#include <QHostAddress>
#include <QSizePolicy>
#include <QtGlobal>

#include <cstdio>

int main()
{
    const QColor color("#336699");
    if (!color.isValid())
        return 1;
    if (color.red() != 0x33 || color.green() != 0x66 || color.blue() != 0x99)
        return 2;

    const QHostAddress loopback(QHostAddress::LocalHost);
    if (!loopback.isLoopback())
        return 3;

    const QSizePolicy policy(QSizePolicy::Preferred, QSizePolicy::Expanding);
    if (policy.horizontalPolicy() != QSizePolicy::Preferred)
        return 4;
    if (policy.verticalPolicy() != QSizePolicy::Expanding)
        return 5;

    std::printf("Qt %s Gui/Widgets value APIs are available\n", QT_VERSION_STR);
    return 0;
}
