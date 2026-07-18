cmake_minimum_required(VERSION 3.16)
project(test_ecm C)  # C 不是 CXX — test_ecm.c 是 C 源

# R34: 实质调用 ECM API — find_package(ECM) 必须成功，否则 cmake configure 失败
find_package(ECM REQUIRED CONFIG)

include(ECMQmLoader)
include(ECMSetupVersion)
ecm_setup_version(${ECM_VERSION}
    VARIABLE_PREFIX ECM
    VERSION_HEADER "${CMAKE_CURRENT_BINARY_DIR}/ecm_test_version.h"
)

# 编译 test_ecm 二进制（CI L0d 门禁要求 conanfile test() 用 self.run() 直跑真二进制）
add_executable(test_ecm src/test_ecm.c)

# cmake.test() 跑此 ctest 验证二进制可执行；conanfile test() 同步用 self.run() 直跑
enable_testing()
add_test(NAME ecm_loaded COMMAND test_ecm)
