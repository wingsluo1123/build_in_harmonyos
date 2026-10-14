// SPDX-License-Identifier: GPL-3.0-or-later
//
// Consumer test for the installed kdsoap-ws-discovery package.
//
// It links the exported CMake target KDSoap::WSDiscoveryClient from
// find_package(KDSoapWSDiscoveryClient) and calls the real public API:
// WSDiscoveryTargetService, WSDiscoveryServiceAggregator and
// WSDiscoveryProbeJob (plus the installed version header). No network is
// required: every check below exercises in-process behaviour only, so the
// program is deterministic on the OHOS build host.
//
// It performs a fixed set of 14 checks and prints "RESULT: N ok, M fail".

#include <cstdio>

#include <QCoreApplication>
#include <QDateTime>
#include <QList>
#include <QSharedPointer>
#include <QUrl>

#include <KDSoapClient/KDQName>

#include "wsdiscoveryclient.h"
#include "wsdiscoveryprobejob.h"
#include "wsdiscoveryserviceaggregator.h"
#include "wsdiscoverytargetservice.h"

#include "kdsoap_wsdiscovery_client_version.h"

static int g_ok = 0;
static int g_fail = 0;

#define CHECK(cond, msg)                                                                 \
    do {                                                                                 \
        if (cond) {                                                                      \
            ++g_ok;                                                                      \
            std::printf("PASS: %s\n", msg);                                              \
        } else {                                                                         \
            ++g_fail;                                                                    \
            std::printf("FAIL: %s (%s:%d)\n", msg, __FILE__, __LINE__);                  \
        }                                                                                \
    } while (0)

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // 1. Default-constructed target service has an empty endpoint reference.
    {
        WSDiscoveryTargetService service;
        CHECK(service.endpointReference().isEmpty(),
              "WSDiscoveryTargetService default ctor leaves endpointReference empty");
    }

    // 2. Endpoint-reference constructor stores the identifier.
    {
        WSDiscoveryTargetService service(QStringLiteral("urn:example:target-1"));
        CHECK(service.endpointReference() == QLatin1String("urn:example:target-1"),
              "WSDiscoveryTargetService(endpointReference) stores the identifier");
    }

    // 3-4. typeList round-trips and isMatchingType compares namespace+localName.
    {
        const KDQName type(QStringLiteral("http://printer.example.org/2003/imaging"),
                           QStringLiteral("PrintBasic"));
        WSDiscoveryTargetService service(QStringLiteral("urn:example:target-2"));
        service.setTypeList(QList<KDQName>() << type);
        CHECK(service.typeList().size() == 1 && service.isMatchingType(type),
              "typeList round-trips and isMatchingType matches namespace+localName");

        KDQName other(QStringLiteral("PrintBasic"));
        other.setNameSpace(QStringLiteral("http://other.example.org/wsdl"));
        CHECK(!service.isMatchingType(other),
              "isMatchingType rejects a type with a different namespace");
    }

    // 5-6. scopeList round-trips and isMatchingScope compares full URLs.
    {
        const QUrl scope(QStringLiteral("onvif://www.onvif.org/Profile/Streaming"));
        WSDiscoveryTargetService service(QStringLiteral("urn:example:target-3"));
        service.setScopeList(QList<QUrl>() << scope);
        CHECK(service.scopeList().size() == 1 && service.isMatchingScope(scope),
              "scopeList round-trips and isMatchingScope matches the stored URL");
        CHECK(!service.isMatchingScope(QUrl(QStringLiteral("onvif://www.onvif.org/Profile/G"))),
              "isMatchingScope rejects a different scope URL");
    }

    // 7. xAddrList round-trips.
    {
        const QUrl xaddr(QStringLiteral("http://prn-example/PRN42/b42-1668-a"));
        WSDiscoveryTargetService service(QStringLiteral("urn:example:target-4"));
        service.setXAddrList(QList<QUrl>() << xaddr);
        CHECK(service.xAddrList().size() == 1 && service.xAddrList().first() == xaddr,
              "xAddrList round-trips the stored XAddrs");
    }

    // 8. lastSeen is invalid until updateLastSeen stamps the current time.
    {
        WSDiscoveryTargetService service(QStringLiteral("urn:example:target-5"));
        const bool wasInvalid = !service.lastSeen().isValid();
        service.updateLastSeen();
        const qint64 ageMs = service.lastSeen().msecsTo(QDateTime::currentDateTime());
        CHECK(wasInvalid && service.lastSeen().isValid() && qAbs(ageMs) < 5000,
              "lastSeen is invalid until updateLastSeen stamps a current timestamp");
    }

    // 9-11. Aggregator emits serviceUpdated and reuses one shared pointer per
    // endpoint reference, while distinct endpoints get distinct pointers.
    {
        WSDiscoveryServiceAggregator aggregator;
        QSharedPointer<WSDiscoveryTargetService> firstSeen;
        QSharedPointer<WSDiscoveryTargetService> secondSeen;
        QSharedPointer<WSDiscoveryTargetService> thirdSeen;
        int emissions = 0;
        QObject::connect(&aggregator, &WSDiscoveryServiceAggregator::serviceUpdated,
                         [&](const QSharedPointer<WSDiscoveryTargetService> &updated) {
                             ++emissions;
                             if (emissions == 1) {
                                 firstSeen = updated;
                             } else if (emissions == 2) {
                                 secondSeen = updated;
                             } else if (emissions == 3) {
                                 thirdSeen = updated;
                             }
                         });

        WSDiscoveryTargetService update1(QStringLiteral("urn:example:aggregated"));
        update1.setScopeList(QList<QUrl>() << QUrl(QStringLiteral("ldap:///ou=engineering")));
        aggregator.updateService(update1);
        CHECK(emissions == 1 && !firstSeen.isNull()
                  && firstSeen->endpointReference() == QLatin1String("urn:example:aggregated"),
              "updateService emits serviceUpdated with the aggregated endpoint reference");

        WSDiscoveryTargetService update2(QStringLiteral("urn:example:aggregated"));
        update2.setXAddrList(QList<QUrl>() << QUrl(QStringLiteral("http://prn-example/PRN42")));
        aggregator.updateService(update2);
        CHECK(emissions == 2 && firstSeen == secondSeen && secondSeen->xAddrList().size() == 1,
              "the same endpoint reference reuses one QSharedPointer and merges new information");

        WSDiscoveryTargetService other(QStringLiteral("urn:example:distinct"));
        aggregator.updateService(other);
        CHECK(emissions == 3 && !thirdSeen.isNull() && thirdSeen != firstSeen
                  && thirdSeen->endpointReference() == QLatin1String("urn:example:distinct"),
              "a different endpoint reference yields a distinct QSharedPointer");
    }

    // 12. Probe job interval default and setter.
    {
        WSDiscoveryClient client;
        WSDiscoveryProbeJob job(&client);
        const int defaultInterval = job.interval();
        job.setInterval(1234);
        CHECK(defaultInterval == 30000 && job.interval() == 1234,
              "WSDiscoveryProbeJob default interval is 30000 and setInterval round-trips");
    }

    // 13. Probe job type/scope filters round-trip through addType/addScope.
    {
        WSDiscoveryClient client;
        WSDiscoveryProbeJob job(&client);
        KDQName type(QStringLiteral("tdn:NetworkVideoTransmitter"));
        type.setNameSpace(QStringLiteral("http://www.onvif.org/ver10/network/wsdl"));
        job.addType(type);
        job.addScope(QUrl(QStringLiteral("onvif://www.onvif.org/Profile/Streaming")));
        CHECK(job.typeList().size() == 1 && job.scopeList().size() == 1
                  && job.typeList().first() == type
                  && job.scopeList().first()
                      == QUrl(QStringLiteral("onvif://www.onvif.org/Profile/Streaming")),
              "WSDiscoveryProbeJob addType/addScope populate the filter lists");
    }

    // 14. The installed ECM version header reports the packaged version.
    {
        CHECK(QString::fromLatin1(WSDISCOVERY_VERSION_STRING) == QLatin1String("0.4.0")
                  && WSDISCOVERY_VERSION_MAJOR == 0 && WSDISCOVERY_VERSION_MINOR == 4
                  && WSDISCOVERY_VERSION_PATCH == 0,
              "installed version header reports 0.4.0");
    }

    std::printf("RESULT: %d ok, %d fail\n", g_ok, g_fail);
    return g_fail == 0 ? 0 : 1;
}
