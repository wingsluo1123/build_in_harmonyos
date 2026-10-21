cmake_minimum_required(VERSION 3.15)
project(test_kcompletion CXX)

# KF6CompletionConfig.cmake calls find_dependency(Qt6Widgets), so Qt6 must
# be findable first.
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(KF6Completion REQUIRED)

add_executable(test_kcompletion test.cpp)
target_link_libraries(test_kcompletion KF6::Completion)

# The test_package test() method runs the binary directly via self.run() so
# the LD_LIBRARY_PATH / offscreen environment is identical on every OHOS
# host; a ctest registration here would be dead configuration, so none is
# added.
