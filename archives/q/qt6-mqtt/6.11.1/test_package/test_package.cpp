// Copyright (C) 2026 OpenHarmony PC Developer.
// SPDX-License-Identifier: BSD-3-Clause
//
// HarmonyOS consumer feasibility test for Qt6::Mqtt.
//
// Verifies that a plain consumer can link against the packaged
// Qt6::Mqtt module on HarmonyOS and exercise its core APIs without an
// external MQTT broker:
//   1. QMqttClient object lifecycle and default state (module loads,
//      shared library resolves)
//   2. MQTT 5.0 protocol selection
//   3. QMqttConnectionProperties setters (session expiry, receive maximum)
//   4. QMqttLastWillProperties setters and client-level last will
//   5. QMqttTopicName validation rules (wildcards rejected in names)
//   6. QMqttTopicFilter wildcard matching

#include <QtCore/QCoreApplication>
#include <QtCore/QDebug>
#include <QtMqtt/QMqttClient>
#include <QtMqtt/QMqttConnectionProperties>
#include <QtMqtt/QMqttTopicFilter>
#include <QtMqtt/QMqttTopicName>

#include <cstdlib>
#include <iostream>

#define CHECK(cond)                                                          \
    do {                                                                     \
        if (!(cond)) {                                                       \
            std::cerr << "FAILED: " #cond " at line " << __LINE__            \
                      << std::endl;                                          \
            return EXIT_FAILURE;                                             \
        }                                                                    \
    } while (false)

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // 1) Module feasibility: instantiate the client on HarmonyOS.
    QMqttClient client;
    CHECK(client.state() == QMqttClient::Disconnected);
    CHECK(client.port() == 0); // documented default: no port set yet

    // 2) MQTT 5.0 protocol version selection.
    client.setProtocolVersion(QMqttClient::MQTT_5_0);
    CHECK(client.protocolVersion() == QMqttClient::MQTT_5_0);

    // 3) MQTT 5.0 connection properties.
    QMqttConnectionProperties connProps;
    connProps.setSessionExpiryInterval(60);
    connProps.setMaximumReceive(100);
    CHECK(connProps.sessionExpiryInterval() == 60);
    CHECK(connProps.maximumReceive() == 100);

    // 4) Last-will properties (client level + MQTT 5.0 will properties).
    client.setWillTopic(QStringLiteral("ohos/pc/status"));
    client.setWillQoS(1);
    CHECK(client.willTopic() == QLatin1String("ohos/pc/status"));
    CHECK(client.willQoS() == 1);

    QMqttLastWillProperties willProps;
    willProps.setWillDelayInterval(30);
    willProps.setMessageExpiryInterval(3600);
    CHECK(willProps.willDelayInterval() == 30);
    CHECK(willProps.messageExpiryInterval() == 3600);
    client.setLastWillProperties(willProps);
    CHECK(client.lastWillProperties().willDelayInterval() == 30);

    // 5) Topic name validation: wildcards are invalid inside a topic name.
    QMqttTopicName validName(QStringLiteral("ohos/pc/qt/mqtt"));
    CHECK(validName.isValid());
    QMqttTopicName invalidName(QStringLiteral("ohos/+/mqtt"));
    CHECK(!invalidName.isValid());
    QMqttTopicName emptyName;
    CHECK(!emptyName.isValid());

    // 6) Topic filter wildcard matching.
    QMqttTopicFilter filter(QStringLiteral("ohos/+/qt/#"));
    CHECK(filter.isValid());
    CHECK(filter.match(validName));
    CHECK(!filter.match(QMqttTopicName(QStringLiteral("other/pc/qt/mqtt"))));

    std::cout << "qt6-mqtt HarmonyOS consumer feasibility test passed"
              << std::endl;
    return EXIT_SUCCESS;
}
