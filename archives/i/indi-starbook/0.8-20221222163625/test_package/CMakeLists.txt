cmake_minimum_required(VERSION 3.15)
project(test_starbook CXX)

find_package(libnova REQUIRED)
find_package(GTest REQUIRED)

# Upstream official unit test (test_starbook.cpp) exercises the public
# protocol-types layer starbook_types.cpp: starbook::CommandResponse
# parsing and starbook::DateTime formatting. Both sources are vendored in
# this directory (starbook_types.cpp is the post-0004 ltrim version;
# CI L0c requires test sources inside test_package/). The tested sources
# only need libnova (ln_equ_to_hequ / ln_lnlat_to_hlnlat via the Equ/LnLat
# helpers) — no libindi, no curl.
add_executable(test_starbook
    test_starbook.cpp
    starbook_types.cpp
)
target_include_directories(test_starbook PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    # starbook_types.h includes <libnova/utility.h> with prefix; the package
    # keeps headers under include/libnova/, so the include ROOT suffices.
    ${libnova_INCLUDE_DIRS}
)
target_link_libraries(test_starbook PRIVATE libnova::libnova GTest::gtest)
set_property(TARGET test_starbook PROPERTY CXX_STANDARD 17)
