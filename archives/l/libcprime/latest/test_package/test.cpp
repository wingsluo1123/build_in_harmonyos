#include <QCoreApplication>
#include <QString>
#include <QDebug>
#include <cprime.h>
#include <stringfunc.h>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);

    // Test CPrime::StringFunc::CapitalizeEachWord
    QString input = "hello world";
    QString result = CPrime::StringFunc::CapitalizeEachWord(input);
    qDebug() << "Input:" << input << "Output:" << result;

    if (result.contains("Hello") && result.contains("World")) {
        return 0;
    }
    return 1;
}
