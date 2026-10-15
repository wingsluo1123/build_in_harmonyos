// test_package/test.cpp — dbg-macro 0.5.1 consumer test
// 通过安装后的 dbg_macro::dbg_macro target 验证公开 API 行为：
// dbg() 返回值语义、多参数形式、pretty_print 容器渲染、dbg::hex / dbg::bin。
// 断言口径与 0.5.1.1（同一上游 v0.5.1 tarball）保持一致。
#include <dbg.h>
#include <cstdint>
#include <cstdio>
#include <sstream>
#include <string>
#include <vector>

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg)                                     \
    do {                                                     \
        ++checks;                                            \
        if (!(cond)) {                                       \
            fprintf(stderr, "FAIL: %s\n", msg);              \
            failures++;                                      \
        }                                                    \
    } while (0)

int main() {
    // 1) dbg() 宏：打印表达式 + 值，并返回表达式的值
    int x = 42;
    int y = dbg(x);
    CHECK(y == 42, "dbg() did not return the value");

    // 2) 复杂表达式 + 多参数形式（两个独立检查）（返回最后一个参数的值）
    auto r = dbg(1 + 2 * 3);
    CHECK(r == 7, "dbg() expression value mismatch");
    int multiple = dbg(1, 2, 1 + 2);
    CHECK(multiple == 3, "multiple-argument dbg() value mismatch");

    // 3) pretty_print：vector 渲染为 {1, 2, 3}
    std::stringstream container;
    dbg::pretty_print(container, std::vector<int>{1, 2, 3});
    CHECK(container.str() == "{1, 2, 3}",
          "pretty_print(vector) rendering mismatch");

    // 4) dbg::hex：16 位整数十六进制渲染
    std::stringstream hex;
    dbg::pretty_print(hex, dbg::hex(static_cast<std::uint16_t>(0xAB12)));
    CHECK(hex.str() == "0xAB12", "dbg::hex rendering mismatch");

    // 5) dbg::bin：8 位整数二进制渲染（含前导零）
    std::stringstream bin;
    dbg::pretty_print(bin, dbg::bin(static_cast<std::uint8_t>(11)));
    CHECK(bin.str() == "0b00001011", "dbg::bin rendering mismatch");

    if (failures > 0) {
        fprintf(stderr, "dbg-macro consumer test: %d check(s) failed\n", failures);
        return 1;
    }
    printf("dbg-macro consumer test: PASS (%d checks)\n", checks);
    return 0;
}
