// test.cpp — qtremoteobjects test_package
// 运行时测试：验证 Qt5RemoteObjects 库可正常加载和使用
#include <QCoreApplication>
#include <QtRemoteObjects/qremoteobjectnode.h>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);
    QRemoteObjectNode node;
    printf("test qtremoteobjects 5.15.2: OK\n");
    return 0;
}
