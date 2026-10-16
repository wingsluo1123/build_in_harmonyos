cmake_minimum_required(VERSION 3.16)
project(lockfree_harmonyos_test LANGUAGES C)

# HarmonyOS 专项测试（可复现构建入口）
# 用法:
#   conan install --requires=lockfree/b08f761900@ohpcd/stable \
#     -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 \
#     --build=never -of <consumer_dir> -g CMakeDeps -g CMakeToolchain
#   cmake -S . -B <build_dir> -DCMAKE_TOOLCHAIN_FILE=<consumer_dir>/generators/conan_toolchain.cmake
#   cmake --build <build_dir> && TMPDIR=$HOME/tmp ctest --test-dir <build_dir> --output-on-failure
find_package(lockfree REQUIRED)

add_executable(ohos_lockfree_api_test ohos_lockfree_api_test.c)
target_link_libraries(ohos_lockfree_api_test PRIVATE lockfree::lockfree)
target_compile_features(ohos_lockfree_api_test PRIVATE c_std_99)

# R03: 新增端到端消费者用例独立入口（跨线程生产→消费流水线 + magicq 完整流转）
find_package(Threads REQUIRED)
add_executable(e2e_consumer_test e2e_consumer_test.c)
target_link_libraries(e2e_consumer_test PRIVATE lockfree::lockfree Threads::Threads)
target_compile_features(e2e_consumer_test PRIVATE c_std_99)

enable_testing()
add_test(NAME ohos_lockfree_api_test COMMAND ohos_lockfree_api_test)
add_test(NAME e2e_consumer_test COMMAND e2e_consumer_test)
