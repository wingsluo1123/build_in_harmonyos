cmake_minimum_required(VERSION 3.15)
project(test_unicon CXX)

# Find the package via Conan-generated CMakeDeps
find_package(unicon REQUIRED)

# 消费者用例：模拟业务上层通过公开 API（ImmClient.h 的 IMM_* 一族）调用
# 进程内形态（-D__DLL_SUPPORT__：链 libimmclient.a + libimm_server.so，
# 与 unicon 主程序同一链接形态）
add_executable(consumer_test consumer_test.cpp)
target_compile_definitions(consumer_test PRIVATE __DLL_SUPPORT__)
target_link_libraries(consumer_test PRIVATE unicon::unicon)

enable_testing()
add_test(NAME consumer_test
         COMMAND consumer_test
                 ${UNICON_PKG_ROOT}/lib/unicon/modules/cce/cce_pinyin.so
                 ${UNICON_PKG_ROOT}/lib/unicon/modules/cce/dict)
