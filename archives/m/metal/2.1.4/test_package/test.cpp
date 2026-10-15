#include <metal.hpp>
#include <type_traits>

int main() {
    // 消费者视角：包含聚合头 metal.hpp，使用 metal 的列表/数值 API。
    using list = metal::list<int, char, double>;
    static_assert(metal::size<list>::value == 3, "list size must be 3");
    static_assert(metal::same<metal::front<list>, int>::value, "front must be int");

    using numbers = metal::numbers<1, 2, 3>;
    static_assert(metal::size<numbers>::value == 3, "numbers size must be 3");

    using sum = metal::add<metal::number<1>, metal::number<2>, metal::number<3>>;
    static_assert(metal::same<sum, metal::number<6>>::value, "1+2+3 must be 6");

    return 0;
}