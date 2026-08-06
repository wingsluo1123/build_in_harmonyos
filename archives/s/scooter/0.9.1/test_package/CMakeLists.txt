cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

# scooter is a Rust application (cargo build), no C library to link.
# test_scooter.c 满足 L0c 门禁（test_package 必须有 test 源文件）；
# 真实验证在 test_package/conanfile.py test() 方法中通过 self.run() 完成。
add_executable(test_scooter test_scooter.c)
