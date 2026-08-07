cmake_minimum_required(VERSION 3.18)
project(test_pavucontrol-qt CXX)

# Find the pavucontrol-qt package
find_package(pavucontrol-qt REQUIRED)

# Simple test: verify the binary path is defined
add_executable(test_pavucontrol-qt src/main.cpp)
target_link_libraries(test_pavucontrol-qt PRIVATE ${PACUONTROL_QT_LIBS})

enable_testing()
add_test(NAME pavucontrol_qt_binary_test COMMAND test_pavucontrol-qt)
