// Consumer test for Qt Connectivity (Bluetooth + NFC) on HarmonyOS PC.
//
// HarmonyOS has no BlueZ / PCSCLite / neard backend, so the build uses Qt's
// in-tree dummy backends: the API surface (address/uuid/device-info parsing,
// NFC data records) is fully functional while device discovery reports no
// local adapter.  The test therefore asserts on the data APIs and on the
// documented "no adapter" behaviour rather than on live devices.
#include <QtCore/QDebug>
#include <QtCore/QCoreApplication>
#include <QtBluetooth/QBluetoothAddress>
#include <QtBluetooth/QBluetoothUuid>
#include <QtBluetooth/QBluetoothDeviceInfo>
#include <QtBluetooth/QBluetoothHostInfo>
#include <QtBluetooth/QBluetoothLocalDevice>
#include <QtNfc/QNdefRecord>
#include <QtNfc/QNdefMessage>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // --- Bluetooth: pure data APIs ---
    QBluetoothAddress address(QStringLiteral("00:11:22:33:44:55"));
    if (address.isNull()) {
        qCritical() << "QBluetoothAddress failed to parse";
        return 1;
    }
    qInfo() << "QtBluetooth OK: address =" << address.toString();

    const QBluetoothUuid uuid(
            QBluetoothUuid::ServiceClassUuid::SerialPort);
    if (uuid.isNull()) {
        qCritical() << "QBluetoothUuid construction failed";
        return 1;
    }
    qInfo() << "QtBluetooth OK: uuid =" << uuid.toString();

    QBluetoothDeviceInfo device(address, QStringLiteral("probe-device"),
                                QBluetoothDeviceInfo::MajorDeviceClass::ComputerDevice);
    device.setRssi(42);
    qInfo() << "QtBluetooth OK: device name =" << device.name()
            << " rssi =" << device.rssi();

    QBluetoothHostInfo hostInfo;
    hostInfo.setName(QStringLiteral("ohos-probe"));
    qInfo() << "QtBluetooth OK: host info name =" << hostInfo.name();

    // No Bluetooth hardware: no local adapter is present, and the API must
    // report that state instead of crashing.
    QBluetoothLocalDevice localDevice;
    qInfo() << "QtBluetooth OK: local adapter valid =" << localDevice.isValid();

    // --- NFC: data record APIs ---
    QNdefRecord record;
    record.setTypeNameFormat(QNdefRecord::NfcRtd);
    record.setType(QByteArrayLiteral("T"));
    record.setPayload(QByteArrayLiteral("\x02""en""probe"));
    QNdefMessage message;
    message.append(record);
    // NB: there is no isNfcRtd() — the format is read back through
    // typeNameFormat(), and the payload round-trips verbatim.
    if (message.size() != 1
            || message.at(0).typeNameFormat() != QNdefRecord::NfcRtd
            || message.at(0).type() != QByteArrayLiteral("T")
            || message.at(0).payload() != QByteArrayLiteral("\x02""en""probe")) {
        qCritical() << "QNdefMessage round trip failed";
        return 1;
    }
    qInfo() << "QtNfc OK: ndef message with" << message.size() << "record(s)";

    qInfo() << "QTCONNECTIVITY-CONSUMER-OK";
    return 0;
}
