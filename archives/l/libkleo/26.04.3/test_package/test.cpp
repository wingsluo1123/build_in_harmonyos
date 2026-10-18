#include <Libkleo/Dn>
#include <QCoreApplication>
#include <QString>
#include <cstdio>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    Kleo::DN dn(QStringLiteral("CN=Harmony,OU=Mail"));
    const QString cn = dn[QStringLiteral("CN")];
    if (cn != QStringLiteral("Harmony")) {
        std::printf("FAIL: unexpected CN: %s\n", qPrintable(cn));
        return 1;
    }
    std::printf("PASS: libkleo DN consumer API (CN=%s)\n", qPrintable(cn));
    return 0;
}
