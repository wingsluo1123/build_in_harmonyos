#include <WSDiscoveryClient>
#include <WSDiscoveryTargetService>

#include <QCoreApplication>
#include <QEventLoop>
#include <QHostAddress>
#include <QTimer>
#include <QUdpSocket>

#include <iostream>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    QUdpSocket portReservation;
    if (!portReservation.bind(QHostAddress::LocalHost, 0)) {
        std::cerr << "could not reserve an IPv4 loopback port\n";
        return 10;
    }
    const quint16 port = portReservation.localPort();
    portReservation.close();

    WSDiscoveryClient client;
    WSDiscoveryTargetService receivedService;
    bool received = false;
    QEventLoop responseLoop;
    QObject::connect(&client, &WSDiscoveryClient::probeMatchReceived, &responseLoop,
                     [&](const WSDiscoveryTargetService &service) {
                         receivedService = service;
                         received = true;
                         responseLoop.quit();
                     });
    client.start(port);

    const QByteArray response = R"xml(<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing"
               xmlns:n1="http://schemas.xmlsoap.org/ws/2005/04/discovery">
  <soap:Header>
    <wsa:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/ProbeMatches</wsa:Action>
    <wsa:MessageID>urn:uuid:12345678-1234-1234-1234-123456789abc</wsa:MessageID>
    <n1:AppSequence InstanceId="1" MessageNumber="1"/>
  </soap:Header>
  <soap:Body>
    <n1:ProbeMatches>
      <n1:ProbeMatch>
        <wsa:EndpointReference><wsa:Address>urn:uuid:harmonyos-loopback-probe</wsa:Address></wsa:EndpointReference>
        <n1:Types xmlns:tdn="http://www.onvif.org/ver10/network/wsdl">tdn:NetworkVideoTransmitter</n1:Types>
        <n1:Scopes>onvif://www.onvif.org/Profile/Streaming</n1:Scopes>
        <n1:XAddrs>http://127.0.0.1:8080/onvif/device_service</n1:XAddrs>
        <n1:MetadataVersion>1</n1:MetadataVersion>
      </n1:ProbeMatch>
    </n1:ProbeMatches>
  </soap:Body>
</soap:Envelope>)xml";

    QUdpSocket sender;
    if (sender.writeDatagram(response, QHostAddress::LocalHost, port) != response.size()) {
        std::cerr << "could not send WS-Discovery ProbeMatches over loopback\n";
        return 11;
    }

    QTimer::singleShot(3000, &responseLoop, &QEventLoop::quit);
    responseLoop.exec();
    if (!received) {
        std::cerr << "HarmonyOS UDP loopback did not deliver ProbeMatches to WSDiscoveryClient\n";
        return 12;
    }
    if (receivedService.endpointReference() != QStringLiteral("urn:uuid:harmonyos-loopback-probe")) {
        std::cerr << "WS-Discovery endpoint reference was not parsed\n";
        return 13;
    }
    if (receivedService.xAddrList().size() != 1
        || receivedService.xAddrList().first() != QUrl(QStringLiteral("http://127.0.0.1:8080/onvif/device_service"))) {
        std::cerr << "WS-Discovery XAddr was not parsed\n";
        return 14;
    }

    std::cout << "OHOS_WSD_LOOPBACK_PROBE_MATCH_PASS\n";
    return 0;
}
