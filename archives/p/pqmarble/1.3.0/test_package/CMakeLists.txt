cmake_minimum_required(VERSION 3.15)
project(test_pqmarble C)

# 消费侧验证走 pkg-config（marble.pc 由上游 meson pkg.generate() 产生，
# PkgConfigDeps 生成同内容 .pc），与真实下游用法一致。
find_package(PkgConfig REQUIRED)
pkg_check_modules(MARBLE REQUIRED IMPORTED_TARGET marble)

add_executable(test_pqmarble test_pqmarble.c)
target_link_libraries(test_pqmarble PRIVATE PkgConfig::MARBLE)
target_link_libraries(test_pqmarble PRIVATE dl)
