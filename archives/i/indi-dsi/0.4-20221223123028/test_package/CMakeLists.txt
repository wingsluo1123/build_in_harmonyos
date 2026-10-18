cmake_minimum_required(VERSION 3.15)
project(test_dsi CXX)

# Consumer probe (R34): exercises tokenize_str() from the vendored Util.cpp
# — a pure-std public helper of the driver, so the probe needs no INDI /
# libusb / cfitsio at all. The vendored sources ship inside the tested
# package (<pkg>/src), making the test a real consumer of package artifacts.
add_executable(test_dsi
    test_dsi.cpp
    ${DSI_SRC_DIR}/Util.cpp
)
target_include_directories(test_dsi PRIVATE ${DSI_SRC_DIR})
set_property(TARGET test_dsi PROPERTY CXX_STANDARD 17)
