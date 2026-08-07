// Test that Imath headers and library are usable.
// This test includes ImathVec.h and creates a Vec3, exercising the Imath API.
#include <Imath/ImathVec.h>
#include <iostream>

int main() {
    Imath::Vec3<float> v1(1.0f, 2.0f, 3.0f);
    Imath::Vec3<float> v2(4.0f, 5.0f, 6.0f);
    Imath::Vec3<float> v3 = v1 + v2;

    std::cout << "Imath test: Vec3 result = ("
              << v3.x << ", " << v3.y << ", " << v3.z << ")" << std::endl;

    // Verify correctness
    if (v3.x == 5.0f && v3.y == 7.0f && v3.z == 9.0f) {
        std::cout << "Imath test PASSED" << std::endl;
        return 0;
    }
    std::cerr << "Imath test FAILED" << std::endl;
    return 1;
}
