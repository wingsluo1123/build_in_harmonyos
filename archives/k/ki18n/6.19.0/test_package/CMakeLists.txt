cmake_minimum_required(VERSION 3.16)
project(test_ki18n CXX)

# R34: 实质调用 KF6::I18n API
find_package(KF6I18n REQUIRED CONFIG)

add_executable(test_ki18n src/test_ki18n.cpp)
target_link_libraries(test_ki18n PRIVATE KF6::I18n)

enable_testing()
add_test(NAME ki18n_link COMMAND test_ki18n)
