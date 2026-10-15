// harmonyos_specific_test.cpp — metal 2.1.4 HarmonyOS 专项测试
//
// 调用当前库：metal（C++14 模板元编程头文件库，编译期模板实例化）
// 验证 OHOS 行为：在 HarmonyOS PC (aarch64) 上用 OHOS 工具链实际编译并运行，
// 确认 metal 的编译期计算结果正确，且运行平台确为 HarmonyOS。
#include <metal.hpp>

#include <sys/utsname.h>
#include <cstdio>
#include <cstring>

// 编译期调用当前库：metal 模板元编程结果（OHOS 工具链 aarch64-unknown-linux-ohos 下实例化）
using list = metal::list<int, char, double>;
static_assert(metal::size<list>::value == 3, "metal::size mismatch");
static_assert(metal::same<metal::front<list>, int>::value, "metal::front mismatch");

using sum = metal::add<metal::number<1>, metal::number<2>, metal::number<3>>;
static_assert(metal::same<sum, metal::number<6>>::value, "metal::add mismatch");

int main() {
    // 运行期验证 OHOS 平台行为：uname 系统调用确认运行平台为 HarmonyOS
    struct utsname uts{};
    int rc = uname(&uts);
    bool is_ohos = (rc == 0) &&
                   (std::strstr(uts.sysname, "HarmonyOS") != nullptr ||
                    std::strstr(uts.sysname, "HongMeng") != nullptr ||
                    std::strstr(uts.version, "HarmonyOS") != nullptr ||
                    std::strstr(uts.version, "HongMeng") != nullptr);

    std::printf("metal harmonyos test: size=%d front_ok=1 add=%d uname_rc=%d is_ohos=%d platform=%s %s\n",
                static_cast<int>(metal::size<list>::value),
                static_cast<int>(sum::value),
                rc,
                is_ohos ? 1 : 0,
                rc == 0 ? uts.sysname : "uname-failed",
                rc == 0 ? uts.release : "");

    if (!is_ohos) {
        std::fprintf(stderr, "FAIL: not running on HarmonyOS platform\n");
        return 1;
    }
    std::printf("PASS: metal 2.1.4 harmonyos-specific test (platform=HarmonyOS, library compile-time results verified)\n");
    return 0;
}