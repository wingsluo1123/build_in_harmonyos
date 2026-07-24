// test.cpp — SPIRV-LLVM-Translator test_package
// 实际测试在 conanfile.py test() 中执行 llvm-spirv 二进制 (R34: 执行被测包的二进制)
// 此文件提供最小编译目标以满足 CI L0b 结构检查

#include <cstdio>

int main() {
    // 验证包已正确安装：实际功能测试由 test() 中的 llvm-spirv --help 执行
    printf("test SPIRV-LLVM-Translator 20.1.0: binary test via conan test()\n");
    return 0;
}
