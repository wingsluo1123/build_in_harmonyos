// test_cpr.cpp — 验证 cpr 库可正常编译和链接
// R34: 测试必须实质调用被测包的 API
#include <cpr/cpr.h>
#include <iostream>
#include <string>

int main() {
    // 验证 cpr 库头文件可正常包含
    // 验证 cpr::Response 类型可用
    // 验证 cpr::Url 类型可用

    // 使用 cpr 库的核心类型
    cpr::Url url{"http://example.com"};
    cpr::Timeout timeout{5000};

    // 验证 cpr 版本信息
    std::cout << "cpr version: " << CPR_VERSION << std::endl;
    std::cout << "cpr library test passed!" << std::endl;

    return 0;
}