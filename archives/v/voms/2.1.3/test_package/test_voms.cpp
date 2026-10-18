// voms 消费者冒烟：链接 libvomsapi 并调用公开 C API VOMS_Init
#include <voms/voms_apic.h>
#include <cstdio>

int main() {
    // VOMS_Init 是 voms 客户端的初始化入口（公开 C API）
    struct vomsdata *vd = VOMS_Init((char *)"", (char *)"");
    std::printf("VOMS_Init() = %p (链接+调用成功)\n", (void *)vd);
    return 0;
}
