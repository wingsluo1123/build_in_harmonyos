cmake_minimum_required(VERSION 3.16)
project(kholidays_test LANGUAGES CXX)

# KF6HolidaysConfig.cmake is installed by the package itself and performs
# find_dependency(Qt6Core); the Qt6 prefix is prepared by the generated
# conan_cmakedeps_paths.cmake in the test_package conanfile.py.
find_package(KF6Holidays REQUIRED)

add_executable(test_kholidays test_kholidays.cpp)
target_link_libraries(test_kholidays PRIVATE KF6::Holidays)
# kholidays 6.18.0 is a C++17 code base (the profile pins compiler.cppstd=17).
target_compile_features(test_kholidays PRIVATE cxx_std_17)
