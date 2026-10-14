/* test_neurosim.cc — 消费者视角验证 libneurosim 公开 API。
 *
 * 上游公开 API 实况（据安装头文件）：
 *   - neurosim/version.h：宏 LIBNEUROSIM_VERSION（字符串 "1.2.0"）+
 *     函数 char *libneurosim_version()（lib 导出）
 *   - neurosim/connection_generator.h：全局命名空间的抽象基类
 *     ConnectionGenerator（纯虚 arity/setMask/start/next）+ 具体内嵌类型
 *     Mask/ClosedInterval/IntervalSet
 * 本测试：版本宏 + 版本函数（真实链接库代码）+ 具体内嵌类型构造 +
 * 抽象接口可由消费者实现并实例化。
 */
#include <cstdio>
#include <cstring>
#include <vector>
/* version.h 为 C 库头文件（无 extern "C" 守卫），函数 libneurosim_version()
 * 在 lib 中以 C 符号导出——以 C++ 包含需包 extern "C" 才能正确链接。 */
extern "C" {
#include <neurosim/version.h>
}
#include <neurosim/connection_generator.h>

#define CHECK(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s (line %d)\n", #cond, __LINE__); \
        return 1; \
    } \
} while (0)

/* 最小具体实现：ConnectionGenerator 是纯抽象接口，消费者需实现纯虚方法。 */
class TestConnectionGenerator : public ConnectionGenerator {
public:
    int arity() override { return 2; }
    void setMask(std::vector<ConnectionGenerator::Mask>&, int) override {}
    void start() override {}
    bool next(int&, int&, double*) override { return false; }
};

int main(void)
{
    /* 1. 版本宏存在且值正确（编译期验证头文件可包含） */
    CHECK(strcmp(LIBNEUROSIM_VERSION, "1.2.0") == 0);

    /* 2. 版本查询函数可链接调用（链接期+运行期证明库可用） */
    char *v = libneurosim_version();
    CHECK(v != NULL && strlen(v) > 0);

    /* 3. ConnectionGenerator 具体内嵌类型可构造（库公开 API 可用） */
    ConnectionGenerator::Mask mask(1, 1);
    CHECK(mask.sources.skip() == 1 && mask.targets.skip() == 1);
    ConnectionGenerator::ClosedInterval ci(0, 1);
    CHECK(ci.first == 0 && ci.last == 1);

    /* 4. 抽象接口可由消费者实现并实例化（生命周期完整，析构不崩溃） */
    TestConnectionGenerator gen;
    CHECK(gen.arity() == 2);

    return 0;
}
