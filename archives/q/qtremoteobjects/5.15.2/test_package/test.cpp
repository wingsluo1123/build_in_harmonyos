// test.cpp — qtremoteobjects test_package
// OHOS 平台限制：无法运行时加载 stripped Qt5 库
// 测试通过 conanfile.py 中的 readelf/nm 静态验证完成
// 此文件仅作为 CMake 构建系统的占位符
#include <cstdio>
int main() {
    printf("qtremoteobjects 5.15.2 test package (static verification mode)\n");
    return 0;
}
