cmake_minimum_required(VERSION 3.15)
project(test_mp3splt-gtk C)

# Find the package via Conan-generated CMakeDeps
find_package(mp3splt-gtk REQUIRED)

add_executable(test_mp3splt-gtk test.c)
target_link_libraries(test_mp3splt-gtk mp3splt-gtk::mp3splt-gtk)

enable_testing()
add_test(NAME test_mp3splt-gtk COMMAND test_mp3splt-gtk)
