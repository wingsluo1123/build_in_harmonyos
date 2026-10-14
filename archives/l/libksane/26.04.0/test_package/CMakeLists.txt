cmake_minimum_required(VERSION 3.16)
project(test_libksane CXX)

# Qt6 first: the KSaneWidgets6 config chains through find_dependency(Qt6Widgets)
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)
find_package(KSaneWidgets6 REQUIRED)

# The upstream install(EXPORT) uses an empty namespace, so the exported target
# is plain KSaneWidgets6; keep the namespaced form as a fallback for future
# upstream changes.
if(TARGET KSaneWidgets6)
    set(KSANE_CONSUMER_TARGET KSaneWidgets6)
elseif(TARGET KSaneWidgets6::KSaneWidgets6)
    set(KSANE_CONSUMER_TARGET KSaneWidgets6::KSaneWidgets6)
else()
    message(FATAL_ERROR "KSaneWidgets6Config.cmake did not export a target")
endif()

# Consumer test 1: public-API assertions without a scanner device.
add_executable(test_libksane test.cpp)
target_link_libraries(test_libksane PRIVATE ${KSANE_CONSUMER_TARGET})

# Consumer test 2: end-to-end scanner workflow (open -> options -> scan ->
# image) driven against the SANE "frontend-tester" virtual backend.
add_executable(test_scan_flow test_scan_flow.cpp)
target_link_libraries(test_scan_flow PRIVATE ${KSANE_CONSUMER_TARGET})

enable_testing()
add_test(NAME test_libksane COMMAND test_libksane)
add_test(NAME test_scan_flow COMMAND test_scan_flow)
