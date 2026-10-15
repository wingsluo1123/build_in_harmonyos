# qt5-qtserialport

Qt5 Serial Port module — provides APIs for accessing serial ports (QSerialPort / QSerialPortInfo).

## OHOS 适配

- 版本: 5.15.2
- 构建系统: qmake
- 依赖: qt5-qtbase/5.15.2.2（Qt Core）
- 源码: download.qt.io everywhere-src tarball（官方单条 URL，R39）
- 模式: qtserialport-opensource-src/5.15.15 CI 绿先例（qtbase 路径修正 + QMAKE_STRIP="" + ELF 自签名）
- 上游测试: tst_qserialport / tst_qserialportinfo（无物理串口对时 initTestCase QSKIP）
