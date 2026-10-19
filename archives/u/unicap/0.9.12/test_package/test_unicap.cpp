// unicap 消费者冒烟：链接 libunicap 并调用公开 C API unicap_check_version
#include <unicap.h>
#include <cstdio>

int main() {
    // unicap 公开 C API：版本检查（简单参数 + 状态返回，验证链接+调用）
    unicap_status_t st = unicap_check_version(1, 0, 0);
    std::printf("unicap_check_version(1,0,0) = %d (链接+调用成功)\n", st);
    return 0;
}
