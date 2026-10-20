#include <QCoreApplication>
#include <QString>
#include <iostream>
#include "qmailaddress.h"

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // CHECK 1: construct a named email address and verify fields.
    QMailAddress addr(QString::fromLatin1("QMF Test"),
                      QString::fromLatin1("qmf-test@example.com"));
    if (addr.isNull()) {
        std::cerr << "FAIL: address is null" << std::endl;
        return 1;
    }
    if (addr.address() != QString::fromLatin1("qmf-test@example.com")) {
        std::cerr << "FAIL: address mismatch: "
                  << addr.address().toStdString() << std::endl;
        return 1;
    }
    if (!addr.isEmailAddress()) {
        std::cerr << "FAIL: isEmailAddress() false" << std::endl;
        return 1;
    }
    std::cout << "CHECK 1 passed: QMailAddress construction" << std::endl;

    // CHECK 2: string round-trip carries display name and mailbox.
    QString text = addr.toString();
    if (!text.contains(QString::fromLatin1("qmf-test@example.com"))) {
        std::cerr << "FAIL: toString lost mailbox: "
                  << text.toStdString() << std::endl;
        return 1;
    }
    std::cout << "CHECK 2 passed: QMailAddress toString round-trip" << std::endl;

    std::cout << "RESULT: 2 passed, 0 failed" << std::endl;
    return 0;
}
