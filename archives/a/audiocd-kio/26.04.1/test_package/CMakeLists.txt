cmake_minimum_required(VERSION 3.16)
project(test_audiocd_kio LANGUAGES CXX)

find_package(AudiocdKio REQUIRED)

add_executable(test_audiocd_kio test_audiocd_kio.cpp)
target_link_libraries(test_audiocd_kio PRIVATE AudiocdKio::AudiocdKio)

enable_testing()
add_test(NAME audiocd_kio_test COMMAND test_audiocd_kio)
