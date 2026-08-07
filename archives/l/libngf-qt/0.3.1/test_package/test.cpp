#include <ngfclient.h>
#include <QCoreApplication>
#include <QString>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);
    // 真实调用 libngf-qt API：创建 NGF 客户端连接
    Ngf::Client client;
    if (!client.isValid()) {
        std::printf("libngf-qt test FAILED: client invalid\n");
        return 1;
    }
    std::printf("libngf-qt test PASSED\n");
    return 0;
}
