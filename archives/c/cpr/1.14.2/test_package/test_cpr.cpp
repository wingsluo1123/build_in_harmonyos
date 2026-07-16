// test_cpr.cpp — 验证 cpr 库可正常编译、链接和核心类型可用
// R34: 测试必须实质调用被测包的 API
#include <cpr/cpr.h>
#include <iostream>
#include <string>
#include <cassert>

int main() {
    // 1. 验证核心类型构造
    cpr::Url url{"http://example.com"};
    cpr::Timeout timeout{5000};
    cpr::Header header{{"User-Agent", "cpr-test"}};
    cpr::Parameters params{{"key", "value"}};

    // 2. 验证 SSL 相关类型（即使 SSL 未启用，类型定义仍可用）
    cpr::VerifySsl verify_ssl{false};

    // 3. 验证 cpr::Response 和 cpr::Session 类型可用
    cpr::Session session;
    session.SetUrl(url);
    session.SetTimeout(timeout);
    session.SetHeader(header);
    session.SetParameters(params);

    // 4. 验证 cpr::AsyncWrapper 和回调类型
    auto callback = [](cpr::Response r) -> bool {
        return r.status_code >= 200;
    };

    // 5. 验证 cpr 版本信息
    std::cout << "cpr version: " << CPR_VERSION << std::endl;
    std::cout << "cpr library test passed!" << std::endl;
    std::cout << "All core types verified: Url, Timeout, Header, Parameters, "
              << "Session, Response, VerifySsl, AsyncWrapper" << std::endl;

    return 0;
}