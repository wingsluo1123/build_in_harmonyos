cmake_minimum_required(VERSION 3.16)
project(test_ecm C)  # C 不是 CXX — test_ecm.c 是 C 源

# R34: 实质调用 ECM API — find_package(ECM) 必须成功，否则 cmake configure 失败
find_package(ECM REQUIRED CONFIG)

# R-CI5: ECM 模块路径注入 CMAKE_MODULE_PATH（find_package(ECM) 不自动设此），
# 否则 include(ECMSetupVersion) 报 "could not find requested file"
# R-CI8: foreach 移入 if(DEFINED ECM_DIR) 块内——ECM_DIR 未定义时 ${ECM_DIR} 展开为空，
# 循环会向 CMAKE_MODULE_PATH 追加 /modules、/kde-modules 等以根目录开头的无效路径。
if(DEFINED ECM_DIR)
    list(APPEND CMAKE_MODULE_PATH "${ECM_DIR}")
    # Conan CMakeDeps 注入的 ECM 模块路径兜底（多子目录拼接）
    foreach(_dir modules kde-modules find-modules toolchain)
        list(APPEND CMAKE_MODULE_PATH "${ECM_DIR}/${_dir}")
    endforeach()
endif()

include(ECMSetupVersion)
# R-CI6: 删 VERSION_HEADER 选项——它调 configure_file 需 ECMVersionHeader.h.in 模板，
# ECM package() 没拷此模板到产物，下游找不到报 "File ... does not exist"。
# 测试只验证 ECM 模块加载链通（find_package + include + ecm_setup_version 无 VERSION_HEADER 即可）
ecm_setup_version("6.19.0"
    VARIABLE_PREFIX ECM_TEST
)

# 编译 test_ecm 二进制（CI L0d 门禁要求 conanfile test() 用 self.run() 直跑真二进制）
add_executable(test_ecm src/test_ecm.c)

# cmake.test() 跑此 ctest 验证二进制可执行；conanfile test() 同步用 self.run() 直跑
enable_testing()
add_test(NAME ecm_loaded COMMAND test_ecm)
