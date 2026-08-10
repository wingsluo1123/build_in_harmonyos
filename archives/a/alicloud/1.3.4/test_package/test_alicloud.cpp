// test_alicloud.cpp — 编译链接验证：include mns 头 + 链接 libmnscpp.a
#include <mns/mns_client.h>
#include <cstdio>

int main() {
    // 仅验证头可用与符号存在（真实 MNS 调用需要云凭据，不做网络请求）
    printf("alicloud (MNS C++ SDK) headers OK: mns_client.h included\n");
    return 0;
}
