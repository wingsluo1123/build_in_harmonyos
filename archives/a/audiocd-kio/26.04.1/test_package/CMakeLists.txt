cmake_minimum_required(VERSION 3.16)
project(test_audiocd_kio CXX)

find_package(audiocd-kio REQUIRED)

add_executable(test_audiocd_kio test_audiocd_kio.cpp)
target_link_libraries(test_audiocd_kio audiocd-kio::audiocd-kio)
