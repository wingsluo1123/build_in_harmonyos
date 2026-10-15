cmake_minimum_required(VERSION 3.16)
project(test_kcontacts5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Same native-config wiring as the library build: the recipe's package_info
# exposes the project-installed KF5ContactsConfig.cmake
# (cmake_find_mode=none), so the test consumes it through
# CMAKE_PREFIX_PATH. AUTOMOC is deliberately NOT enabled (no local
# signals/slots in the test body; the Qt5 configs on this chain export no
# Qt5::moc target) - kjobwidgets5 precedent.
find_package(Qt5 5.15.2 REQUIRED COMPONENTS Core Gui)
find_package(KF5Contacts 5.116.0 REQUIRED)

add_executable(test_kcontacts5 test.cpp)
target_link_libraries(test_kcontacts5 PRIVATE Qt5::Core Qt5::Gui KF5::Contacts)

# /proc/self/maps reports the bare soname on OHOS, so give the test the real
# packaged library path to assert its ELF adaptation properties (R53).
target_compile_definitions(test_kcontacts5 PRIVATE
    KCONTACTS_SO_PATH="$<TARGET_FILE:KF5::Contacts>")

enable_testing()
add_test(NAME test_kcontacts5 COMMAND test_kcontacts5)
