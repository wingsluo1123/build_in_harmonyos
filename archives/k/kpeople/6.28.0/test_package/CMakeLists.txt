cmake_minimum_required(VERSION 3.15)
project(test_kpeople CXX)

find_package(Qt6 6.11.1 CONFIG REQUIRED COMPONENTS Gui Widgets)
find_package(KF6People 6.28.0 CONFIG REQUIRED)

add_executable(test_kpeople test.cpp)
target_link_libraries(test_kpeople KF6::People KF6::PeopleWidgets KF6::PeopleBackend)

# OHOS-specific consumer check: the executable must reference KF6People
# through the library SONAME (relative DT_NEEDED) and must not bake
# slash-qualified absolute paths in, the property the recipe-layer SONAME
# override (CMAKE_USER_MAKE_RULES_OVERRIDE) plus the unversioned naming
# (CMAKE_PLATFORM_NO_VERSIONED_SONAME, HMDFS rejects symlinks) exists to
# guarantee.
add_executable(test_kpeople_ohos test_ohos_soname.cpp)
target_link_libraries(test_kpeople_ohos KF6::People)

if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    set_target_properties(test_kpeople PROPERTIES BUILD_RPATH "$ORIGIN")
    target_link_options(test_kpeople PRIVATE "-Wl,--disable-new-dtags")
    set_target_properties(test_kpeople_ohos PROPERTIES BUILD_RPATH "$ORIGIN")
    target_link_options(test_kpeople_ohos PRIVATE "-Wl,--disable-new-dtags")
    target_compile_definitions(test_kpeople_ohos PRIVATE TP_REQUIRE_OHOS)
endif()

enable_testing()
add_test(NAME test_kpeople COMMAND test_kpeople)
add_test(NAME test_kpeople_ohos COMMAND test_kpeople_ohos)
