#include <cstdlib>
#include <iostream>
#include <string>

#include "xeus/xeus.hpp"
#include "xeus/xguid.hpp"
#include "xeus/xhelper.hpp"
#include "xeus/xsystem.hpp"
#include "xeus/xbasic_fixed_string.hpp"

// test_package 消费者验证（R34：必须调用被测包 API，禁止空壳 print-only）
// 模拟内核上层消费者：使用 xeus 公开 API 构造 Jupyter 协议 reply JSON、
// 生成内核会话 GUID、查询系统路径并验证可观察结果。

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
    std::cout << "xeus consumer test (version "
              << XEUS_VERSION_MAJOR << "." << XEUS_VERSION_MINOR << "." << XEUS_VERSION_PATCH
              << ")" << std::endl;

    // 1. 版本宏（业务上用于 Jupyter 内核协议协商）
    check(XEUS_VERSION_MAJOR == 5 && XEUS_VERSION_MINOR == 0 && XEUS_VERSION_PATCH == 0,
          "version macros == 5.0.0");
    std::string proto = XEUS_KERNEL_PROTOCOL_VERSION;
    check(!proto.empty(), "kernel protocol version string non-empty");

    // 2. xguid：内核会话标识（UUID 形式），调用 xeus::new_xguid 公开 API
    xeus::xguid g = xeus::new_xguid();
    std::cout << "  guid=" << g << std::endl;
    check(g.size() > 0, "new_xguid non-empty");

    // 3. xhelper：Jupyter 协议 reply JSON 构造（业务公开 API，结果可观察）
    nl::json reply = xeus::create_successful_reply();
    check(reply.contains("status") && reply["status"] == "ok",
          "create_successful_reply has status ok");
    std::cout << "  reply=" << reply.dump() << std::endl;

    nl::json complete = xeus::create_complete_reply(nl::json::array({"print"}), 0, 5);
    check(complete.contains("matches") && complete["matches"].is_array(),
          "create_complete_reply contains matches array");
    check(complete.contains("cursor_start") && complete["cursor_start"] == 0,
          "create_complete_reply cursor_start");
    check(complete.contains("cursor_end") && complete["cursor_end"] == 5,
          "create_complete_reply cursor_end");
    std::cout << "  complete=" << complete.dump() << std::endl;

    nl::json incomplete = xeus::create_is_complete_reply("incomplete");
    check(incomplete.contains("status") && incomplete["status"] == "incomplete",
          "create_is_complete_reply status incomplete");
    std::cout << "  incomplete=" << incomplete.dump() << std::endl;

    // 4. xsystem：会话运行时路径（业务上用于临时文件/调试器路径解析）
    std::string tmp = xeus::get_temp_directory_path();
    check(!tmp.empty(), "temp directory path non-empty");
    std::cout << "  tmp=" << tmp << std::endl;
    int pid = xeus::get_current_pid();
    check(pid > 0, "current pid > 0");
    std::cout << "  pid=" << pid << std::endl;

    // 5. xbasic_fixed_string 公开 API（内核消息头/签名使用）
    xeus::xbasic_fixed_string<char> fs("kernel-header");
    check(fs == "kernel-header", "fixed_string equality");
    check(fs.find("kernel") == 0, "fixed_string find");

    std::cout << (failures == 0 ? "CONSUMER TEST PASSED" : "CONSUMER TEST FAILED")
              << " (failures=" << failures << ")" << std::endl;
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
