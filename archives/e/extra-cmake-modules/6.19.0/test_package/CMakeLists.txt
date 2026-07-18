cmake_minimum_required(VERSION 3.16)
project(test_ecm CXX)

# R34: 实质调用 ECM API — find_package(ECM) 必须成功，否则 cmake configure 失败
find_package(ECM REQUIRED CONFIG)

include(ECMQmLoader)
include(ECMSetupVersion)
ecm_setup_version(${ECM_VERSION}
    VARIABLE_PREFIX ECM
    VERSION_HEADER "${CMAKE_CURRENT_BINARY_DIR}/ecm_test_version.h"
)

# 如果 ECM 模块能被正确加载并宏执行成功，configure 阶段已通过
# cmake.test() 跑 ctest 验证 configure → build → test 全链通
enable_testing()
add_test(NAME ecm_loaded COMMAND ${CMAKE_COMMAND} --version)
