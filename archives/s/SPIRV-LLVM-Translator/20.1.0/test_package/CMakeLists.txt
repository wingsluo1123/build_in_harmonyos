cmake_minimum_required(VERSION 3.15)
project(test_spirv_llvm_translator CXX)

# 最小编译目标；实际测试在 conanfile.py test() 中执行 llvm-spirv 二进制 (R34)
add_executable(test_spirv_llvm_translator test.cpp)

enable_testing()
add_test(NAME test_spirv_llvm_translator COMMAND test_spirv_llvm_translator)
