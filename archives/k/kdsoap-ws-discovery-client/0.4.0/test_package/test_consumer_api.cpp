#include <KDSoapClient/KDQName>
#include <WSDiscoveryTargetService>

#include <QUrl>

#include <iostream>

int main()
{
    WSDiscoveryTargetService service(QStringLiteral("urn:uuid:consumer-test"));
    const KDQName expectedType(QStringLiteral("urn:example:device"), QStringLiteral("Camera"));
    const KDQName otherType(QStringLiteral("urn:example:device"), QStringLiteral("Printer"));
    const QUrl expectedScope(QStringLiteral("onvif://www.onvif.org/Profile/Streaming"));

    service.setTypeList({expectedType});
    service.setScopeList({expectedScope});

    if (service.endpointReference() != QStringLiteral("urn:uuid:consumer-test"))
        return 1;
    if (!service.isMatchingType(expectedType) || service.isMatchingType(otherType))
        return 2;
    if (!service.isMatchingScope(expectedScope))
        return 3;

    std::cout << "KDSoapWSDiscoveryClient installed consumer API PASS\n";
    return 0;
}
