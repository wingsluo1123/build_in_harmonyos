cmake_minimum_required(VERSION 3.16)
project(test_purpose LANGUAGES CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KF6Purpose REQUIRED CONFIG)

add_executable(test_purpose test_purpose.cpp)
target_link_libraries(test_purpose PRIVATE Qt6::Core Qt6::Gui KF6::Purpose)

enable_testing()
add_test(NAME test_purpose COMMAND test_purpose)
# test_purpose exits 77 when the sandbox cannot host a KIO worker and the
# byte-for-byte export check therefore did not run; ctest then reports the test
# as Skipped instead of turning "not executed" into a green "Passed".
set_tests_properties(test_purpose PROPERTIES SKIP_RETURN_CODE 77)
