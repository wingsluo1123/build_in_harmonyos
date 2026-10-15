#include <QSerialPort>
#include <QSerialPortInfo>
#include <QtGlobal>
#include <cstdio>

// Consumer-side smoke test for qt5-qtserialport on OHOS:
// no physical serial device is required — construction, port enumeration,
// property accessors and error reporting must all work end to end.
int main(int argc, char **argv)
{
    Q_UNUSED(argc);
    Q_UNUSED(argv);

    // QSerialPortInfo::availablePorts() exercises the platform backend
    // (qserialportinfo_unix.cpp): /sys/class/tty enumeration on OHOS.
    const QList<QSerialPortInfo> ports = QSerialPortInfo::availablePorts();
    for (const QSerialPortInfo &port : ports) {
        std::printf("serial port: %s\n", port.portName().toUtf8().constData());
    }

    // QSerialPortInfo: default constructor / accessors must work even with
    // no physical serial device present on the device under test.
    QSerialPortInfo emptyInfo;
    if (!emptyInfo.portName().isEmpty())
        return 1;

    // QSerialPort: construct a port object bound to a (possibly absent)
    // device and verify state/error reporting works end to end.
    QSerialPort port;
    if (port.isOpen())
        return 2;
    port.setPortName("ttyS0");
    if (port.portName() != "ttyS0")
        return 3;
    const QSerialPort::SerialPortError openError = port.error();
    Q_UNUSED(openError); // error() must be callable without crashing

    // Property setters/getters round-trip (works without opening a device).
    port.setBaudRate(QSerialPort::Baud9600);
    if (port.baudRate() != QSerialPort::Baud9600)
        return 4;

    std::printf("Qt %s QSerialPort/QSerialPortInfo work, %lld port(s)\n",
                QT_VERSION_STR, static_cast<long long>(ports.size()));
    return 0;
}
