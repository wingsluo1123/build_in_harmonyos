cmake_minimum_required(VERSION 3.18)
project(test_pavucontrol_qt CXX)

# Test: verify pavucontrol-qt binary can be found and is a valid executable
add_executable(test_pavucontrol_qt src/main.cpp)

enable_testing()
add_test(NAME pavucontrol_qt_binary_test COMMAND test_pavucontrol_qt)
