/*
 * test_package for wf-utils 0.4.0 (HarmonyOS PC)
 *
 * 鸿蒙特有冒烟测试：实质调用 wf-utils 核心 API——
 *   wf::variant_t（std::variant 别名）/ wf::is_int / wf::is_string / wf::is_bool
 * 验证工具库在 OHOS 上可正常构造 variant 并做类型判断。
 */
#include <cstdio>
#include <string>
#include <wayfire/variant.hpp>

int main(void) {
    wf::variant_t vi = 42;
    if (!wf::is_int(vi)) {
        std::fprintf(stderr, "FAIL: is_int(42) should be true\n");
        return 1;
    }
    if (wf::is_string(vi)) {
        std::fprintf(stderr, "FAIL: is_string(42) should be false\n");
        return 1;
    }

    wf::variant_t vs = std::string("wayfire");
    if (!wf::is_string(vs)) {
        std::fprintf(stderr, "FAIL: is_string('wayfire') should be true\n");
        return 1;
    }

    wf::variant_t vb = true;
    if (!wf::is_bool(vb)) {
        std::fprintf(stderr, "FAIL: is_bool(true) should be true\n");
        return 1;
    }

    std::printf("wf-utils smoke test OK (variant_t, is_int/is_string/is_bool)\n");
    return 0;
}
