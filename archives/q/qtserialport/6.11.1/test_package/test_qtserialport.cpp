#include <QSerialPort>
#include <QSerialPortInfo>
#include <QtGlobal>

#include <cstdio>

int main(int argc, char **argv)
{
    Q_UNUSED(argc);
    Q_UNUSED(argv);

    // QSerialPort: construction and configuration API
    QSerialPort port;
    port.setBaudRate(115200);
    port.setDataBits(QSerialPort::Data8);
    port.setParity(QSerialPort::NoParity);
    port.setStopBits(QSerialPort::OneStop);
    if (port.baudRate() != 115200)
        return 1;
    if (port.dataBits() != QSerialPort::Data8)
        return 2;

    // QSerialPortInfo: enumerate available ports (may be empty on CI, not an error)
    const QList<QSerialPortInfo> ports = QSerialPortInfo::availablePorts();
    const int count = ports.size();
    if (count < 0)
        return 3;

    std::printf(
        "Qt %s QSerialPort/QSerialPortInfo work (%d serial port(s) enumerated)\n",
        QT_VERSION_STR, count
    );
    return 0;
}
