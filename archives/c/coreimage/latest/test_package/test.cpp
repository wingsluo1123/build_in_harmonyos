#include <QCoreApplication>
#include <QString>
#include <QDebug>
#include <cprime/cprime.h>
#include <cprime/stringfunc.h>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);

    // Test that libcprime (coreimage's dependency) is usable
    QString input = "hello world";
    QString result = CPrime::StringFunc::CapitalizeEachWord(input);
    qDebug() << "CapitalizeEachWord:" << result;

    if (result.contains("Hello") && result.contains("World")) {
        return 0;
    }
    return 1;
}
