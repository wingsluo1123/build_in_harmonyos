// test_package 消费者测试：实际调用 cpp-member-accessor 的 API
// 验证 header-only 库可被下游消费者通过 find_package(accessor) 使用，
// 并能实际访问类的私有成员（核心功能）。用法对齐上游 tests/ 惯用法
// （MakeProxy 显式实例化 + accessMember/callFunction）。
//
// R34 加固：本文件不再依赖 assert()——Release/NDEBUG 下 assert 会展开为
// ((void)0) 使校验整体丢失（等效空壳）。改为自计失败数的 CHECK 宏，
// 统计失败数并以非零退出码返回，保证任何 build_type 下校验真实生效。
#include <accessor/accessor.hpp>

#include <cstdio>
#include <string>

namespace {

// CHECK 宏：条件为假时打印失败并累计失败数（不依赖 assert/NDEBUG）。
int g_failures = 0;

#define CHECK(cond)                                                          \
    do {                                                                      \
        if (!(cond)) {                                                        \
            std::fprintf(stderr, "[test-package] CHECK FAILED: %s (line %d)\n", \
                         #cond, __LINE__);                                    \
            ++g_failures;                                                     \
        }                                                                     \
    } while (0)

} // namespace

class PrivateBox
{
public:
    PrivateBox() = default;
    PrivateBox(int secret, std::string name) : secret_(secret), name_(std::move(name)) {}

private:
    int secret_ = 42;
    std::string name_ = "hidden";

    int triple(int x) { return x * 3; }
    int addTo(int x) const { return secret_ + x; }
};

// 显式实例化模板以穿透访问控制（标准允许：显式实例化忽略访问限定符）
struct SecretAccessor : accessor::MemberWrapper<PrivateBox, int> {};
template class accessor::MakeProxy<SecretAccessor, &PrivateBox::secret_>;

struct NameAccessor : accessor::MemberWrapper<PrivateBox, std::string> {};
template class accessor::MakeProxy<NameAccessor, &PrivateBox::name_>;

struct TripleAccessor : accessor::FunctionWrapper<PrivateBox, int, int> {};
template class accessor::MakeProxy<TripleAccessor, &PrivateBox::triple>;

struct AddToAccessor : accessor::ConstFunctionWrapper<PrivateBox, int, int> {};
template class accessor::MakeProxy<AddToAccessor, &PrivateBox::addTo>;

int main()
{
    PrivateBox box(100, "visible");

    // 读取私有成员
    CHECK(accessor::accessMember<SecretAccessor>(box).get() == 100);
    CHECK(accessor::accessMember<NameAccessor>(box).get() == "visible");

    // 修改私有成员
    accessor::accessMember<SecretAccessor>(box).get() = 7;
    CHECK(accessor::accessMember<SecretAccessor>(box).get() == 7);

    // 调用私有成员函数
    CHECK(accessor::callFunction<TripleAccessor>(box, 5) == 15);
    CHECK(accessor::callFunction<AddToAccessor>(box, 3) == 10);

    if (g_failures == 0) {
        std::printf("[test-package] ALL CHECKS PASSED (5 checks, Release/NDEBUG-safe)\n");
        return 0;
    }
    std::fprintf(stderr, "[test-package] %d CHECK(s) FAILED\n", g_failures);
    return 1;
}
