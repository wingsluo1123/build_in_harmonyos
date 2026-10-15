cmake_minimum_required(VERSION 3.15)
project(test_modemmanager C)

find_package(ModemManager CONFIG REQUIRED)

add_executable(test_modemmanager test_modemmanager.c)
target_link_libraries(test_modemmanager PRIVATE ModemManager::ModemManager)

enable_testing()
add_test(NAME test_modemmanager COMMAND test_modemmanager)
