#include <Libkleo/Hex>

#include <QByteArray>
#include <QCoreApplication>
#include <QDebug>

#include <string>

namespace
{
int fail(const char *message)
{
    qCritical().noquote() << message;
    return 1;
}
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // Libkleo's hexencode/hexdecode are URL-style percent encoding, not plain hex:
    // printable characters are passed through, ' ' becomes '+', and
    // " # $ % ' + = are percent-encoded. See upstream autotests/hextest.cpp.
    if (Kleo::hexencode(std::string("abc")) != std::string("abc")) {
        return fail("std::string passthrough encoding failed");
    }
    if (Kleo::hexencode(std::string("a b")) != std::string("a+b")) {
        return fail("std::string space encoding failed");
    }
    if (Kleo::hexencode(std::string("50%")) != std::string("50%25")) {
        return fail("std::string percent encoding failed");
    }
    if (Kleo::hexdecode(std::string("a+b")) != std::string("a b")) {
        return fail("std::string plus decoding failed");
    }
    if (Kleo::hexdecode(std::string("%20")) != std::string(" ")) {
        return fail("std::string percent decoding failed");
    }

    const QByteArray encoded = Kleo::hexencode(QByteArrayLiteral("Qt 6"));
    if (encoded != QByteArrayLiteral("Qt+6")) {
        return fail("QByteArray hex encoding failed");
    }
    if (Kleo::hexdecode(encoded) != QByteArrayLiteral("Qt 6")) {
        return fail("QByteArray hex decoding failed");
    }

    qInfo().noquote() << "PASS: libkleo hex helpers encoded and decoded data";
    return 0;
}
