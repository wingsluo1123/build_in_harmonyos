cmake_minimum_required(VERSION 3.16)
project(test_knotifications LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC OFF)

# Qt6Gui is required because KF6NotificationsConfig.cmake does
# find_dependency(Qt6Gui) and the exported KF6::Notifications target
# carries Qt6::Core/Qt6::Gui in its interface.
find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KF6Notifications REQUIRED)

add_executable(test_knotifications test.cpp)
target_link_libraries(
    test_knotifications
    PRIVATE
        Qt6::Core
        Qt6::Gui
        KF6::Notifications
)

# OHOS-specific consumer check: parses its own ELF dynamic section plus
# the loaded libKF6Notifications.so (re-opened via the LD_LIBRARY_PATH
# candidate list, /proc/self/maps pathname as fallback) and validates the
# SONAME-based linkage the recipe guarantees: a bare DT_SONAME and no
# slash-qualified DT_NEEDED entries (platform E537).
add_executable(test_knotifications_ohos test_ohos_soname.cpp)
target_link_libraries(
    test_knotifications_ohos
    PRIVATE
        Qt6::Core
        Qt6::Gui
        KF6::Notifications
)

enable_testing()
add_test(NAME test_knotifications COMMAND test_knotifications)
add_test(NAME test_knotifications_ohos COMMAND test_knotifications_ohos)
