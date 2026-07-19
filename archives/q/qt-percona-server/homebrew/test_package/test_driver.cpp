#include <QCoreApplication>
#include <QtSql>
#include <cassert>
#include <iostream>

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    // Verify the QMYSQL driver is available
    const QStringList drivers = QSqlDatabase::drivers();
    std::cout << "Available SQL drivers:" << std::endl;
    for (const QString &d : drivers) {
        std::cout << "  " << d.toStdString() << std::endl;
    }

    assert(drivers.contains("QMYSQL"));

    QSqlDatabase db = QSqlDatabase::addDatabase("QMYSQL");
    assert(db.isValid());
    assert(db.driverName() == "QMYSQL");

    std::cout << "QMYSQL driver loaded successfully" << std::endl;
    return 0;
}
