#include <stdio.h>
#include <xsimd/xsimd.hpp>

int main() {
    xsimd::batch<float> v(1.0f, 2.0f, 3.0f, 4.0f);
    v = v + v;
    printf("test xsimd 13.0.0: OK (batch add: %f)\n", (float)xsimd::hadd(v));
    return 0;
}
