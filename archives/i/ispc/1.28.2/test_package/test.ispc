// test_package/test.ispc — 真实 SPMD 内核（R34 反空壳：必须真跑被测产物的 codegen + 链接 + 执行）
// 用 neon 目标（本平台 aarch64）编译为对象文件，由 test.cpp 调用并校验数值结果。

export void add_arrays(uniform float a[], uniform float b[], uniform float c[], uniform int n) {
    foreach (i = 0 ... n) {
        c[i] = a[i] + b[i];
    }
}

export uniform float dot_product(uniform float a[], uniform float b[], uniform int n) {
    float acc = 0;
    foreach (i = 0 ... n) {
        acc += a[i] * b[i];
    }
    return reduce_add(acc);
}
