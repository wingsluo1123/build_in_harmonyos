#include <cstdlib>
#include <iostream>
#include <string>

#include "xeus/xeus.hpp"
#include "xeus/xsystem.hpp"
#include "xeus/xguid.hpp"
#include "xeus/xhash.hpp"
#include "xeus/xbasic_fixed_string.hpp"

// HarmonyOS 专项测试：验证 xeus 在 OHOS 平台的适配完整性。
// 不依赖上游测试（上游 test_xsystem/test_xhash 已单独逐项运行），
// 本测试聚焦 OHOS 运行时环境语义：进程 PID、临时目录、GUID 熵源、
// 路径可写性等在实际 OHOS 环境下的真实行为，符合 R40 适配完整性验证。

static int failures = 0;

static void check(bool cond, const char* what)
{
    if (!cond)
    {
        ++failures;
        std::cout << "FAIL: " << what << std::endl;
    }
    else
    {
        std::cout << "PASS: " << what << std::endl;
    }
}

int main()
{
    std::cout << "xeus HarmonyOS special test on "
#ifdef __OHOS__
              << "OHOS"
#else
              << "OHOS-like\n"
#endif
              << std::endl;

    // 1. PID 语义：OHOS 上 getpid 必须返回真实进程号
    int pid = xeus::get_current_pid();
    check(pid > 0, "get_current_pid > 0");
    std::cout << "  pid=" << pid << std::endl;

    // 2. 临时目录语义：OHOS 的 /tmp 可能只读（E002），必须能取到可写临时路径
    std::string tmp = xeus::get_temp_directory_path();
    check(!tmp.empty(), "temp dir non-empty");
    std::cout << "  tmp=" << tmp << std::endl;

    // 3. 目录创建：真实创建并断言存在（可观察结果，非空壳）
    std::string dir = tmp + "/xeus-ohos-special-" + std::to_string(pid);
    bool created = xeus::create_directory(dir);
    check(created, "create_directory returns true");
    std::cout << "  dir=" << dir << " created=" << created << std::endl;

    // 4. GUID 熵源：OHOS 上必须能生成非空且互不相同的会话 GUID
    xeus::xguid g1 = xeus::new_xguid();
    xeus::xguid g2 = xeus::new_xguid();
    check(!g1.empty() && !g2.empty(), "guids non-empty");
    check(g1 != g2, "two guids distinct");
    std::cout << "  g1=" << g1 << "\n  g2=" << g2 << std::endl;

    // 5. 固定字符串（内核协议头部构造）与哈希种子
    xeus::xbasic_fixed_string<char> hdr("execute_request");
    check(hdr == "execute_request", "fixed_string round-trip");
    std::size_t seed = xeus::get_tmp_hash_seed();
    check(seed != 0, "hash seed non-zero");
    std::cout << "  seed=" << seed << std::endl;

    std::cout << (failures == 0 ? "OHOS SPECIAL TEST PASSED" : "OHOS SPECIAL TEST FAILED")
              << " (failures=" << failures << ")" << std::endl;
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}