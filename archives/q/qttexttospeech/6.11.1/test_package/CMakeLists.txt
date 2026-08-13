cmake_minimum_required(VERSION 3.16)
project(qttexttospeech_test LANGUAGES CXX)

# test_package.cpp 含 Q_OBJECT 类（TtsProbe），需 AUTOMOC 生成 moc。
set(CMAKE_AUTOMOC ON)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core TextToSpeech)

add_executable(test_package test_package.cpp)
target_compile_features(test_package PRIVATE cxx_std_17)
target_link_libraries(
    test_package PRIVATE Qt6::TextToSpeech Qt6::Core
)
