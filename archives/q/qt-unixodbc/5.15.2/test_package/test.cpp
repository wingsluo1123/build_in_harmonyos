#include <QSqlDatabase>
#include <QStringList>
#include <cstdio>

int main() {
    // Verify Qt5Sql library is functional
    QSqlDatabase db;
    QStringList drivers = QSqlDatabase::drivers();
    printf("Qt5Sql loaded. Available drivers: %d\n", drivers.size());
    printf("Test passed.\n");
    return 0;
}
