cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

# tlrc is a Rust application (cargo build), no C library to link.
# test_tlrc.c 满足 L0c 门禁（test_package 必须有 test 源文件）；
# 真实验证在 test_package/conanfile.py test() 方法中通过 self.run() 完成。
add_executable(test_tlrc test_tlrc.c)
