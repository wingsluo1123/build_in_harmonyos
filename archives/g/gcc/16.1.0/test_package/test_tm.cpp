// gcc 16.1.0 -fgnu-tm C++ 消费者测试。
// 验证安装后的 GCC C++ 前端（cc1plus）+ libitm + libstdc++ 能用 -fgnu-tm
// 编译并运行事务代码，且 C++ 异常能穿透事务边界（对应上游 eh-1.C）。
#include <cstdio>
#include <cstdlib>

static int g;
static int dothrow;

static void f1()
{
    g++;
    if (dothrow)
        throw 1;
}

static void f2()
{
    __transaction_atomic {
        f1();
    }
}

int main()
{
    int failures = 0;

    /* 对应上游 eh-1.C：异常穿透事务边界，事务回滚后 g 仍为 2 */
    dothrow = 0;
    f2();

    dothrow = 1;
    try {
        f2();
    } catch (...) {
    }

    if (g != 2) {
        std::printf("FAIL: g=%d expected 2\n", g);
        failures++;
    }

    if (failures == 0) {
        std::printf("C++ TM ALL PASSED\n");
        return 0;
    }
    std::printf("C++ TM %d FAILURE(S)\n", failures);
    return 1;
}
