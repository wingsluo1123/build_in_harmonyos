cmake_minimum_required(VERSION 3.16)
project(test_kcontacts LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC OFF)

# Qt6Gui is required because KF6ContactsConfig.cmake does
# find_dependency(Qt6Gui) and the exported KF6::Contacts target carries
# Qt6::Core in its interface.
find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KF6Contacts REQUIRED)

add_executable(test_kcontacts test.cpp)
target_link_libraries(
    test_kcontacts
    PRIVATE
        Qt6::Core
        KF6::Contacts
)

# OHOS-specific consumer check: parses its own ELF dynamic section plus
# the loaded libKF6Contacts.so (located via /proc/self/maps) and asserts
# the SONAME-based linkage the recipe guarantees: a bare DT_SONAME and no
# slash-qualified DT_NEEDED entries (platform E537).
add_executable(test_kcontacts_ohos test_ohos_soname.cpp)
target_link_libraries(
    test_kcontacts_ohos
    PRIVATE
        Qt6::Core
        KF6::Contacts
)

enable_testing()
add_test(NAME test_kcontacts COMMAND test_kcontacts)
add_test(NAME test_kcontacts_ohos COMMAND test_kcontacts_ohos)
