// test_package/test.cpp — 消费 ispc 产物：调用 ispc 生成的 SPMD 内核并校验数值（R34 反空壳）
//
// ispc 生成的 C 头把导出函数放在 `namespace ispc { ... }` 内（函数本身仍是 extern "C" 链接），
// 因此 C++ 侧必须按 `ispc::<name>` 限定名调用。设备轮实测：不加限定名会报
//   error: use of undeclared identifier 'add_arrays'; did you mean 'ispc::add_arrays'?
#include <cmath>
#include <cstdio>

#include "ispc_probe.h"   // ispc -h 生成（namespace ispc）

int main() {
    const int n = 64;
    float a[n], b[n], c[n];
    for (int i = 0; i < n; ++i) {
        a[i] = static_cast<float>(i) * 0.5f;
        b[i] = static_cast<float>(i) + 1.0f;
        c[i] = -1.0f;
    }
    ispc::add_arrays(a, b, c, n);
    for (int i = 0; i < n; ++i) {
        if (c[i] != a[i] + b[i]) {
            std::printf("FAIL add_arrays at %d: %f != %f\n", i, c[i], a[i] + b[i]);
            return 1;
        }
    }

    const float dot = ispc::dot_product(a, b, n);
    float expect = 0.0f;
    for (int i = 0; i < n; ++i) expect += a[i] * b[i];
    if (std::fabs(dot - expect) > 1e-3f * std::fabs(expect)) {
        std::printf("FAIL dot_product: %f != %f\n", dot, expect);
        return 1;
    }
    std::printf("ispc probe ok: add_arrays(%d) + dot_product = %f\n", n, dot);
    return 0;
}
