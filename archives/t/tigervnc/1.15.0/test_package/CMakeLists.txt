cmake_minimum_required(VERSION 3.15)
project(tigervnc_consumer_test CXX)

# Consumer-side verification: build against the *installed* headers and the
# exported tigervnc::rfb target only. This proves the package is actually
# consumable on the target platform and that the RFB core links and runs.
#
# The X11/FLTK free subset of upstream's own tests/unit is executed in the
# recipe's build() step instead, where the pristine sources and the generated
# config.h are available. See MANIFEST.yml for both halves of the coverage.
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(tigervnc REQUIRED)

add_executable(test_tigervnc test_tigervnc.cxx)
target_link_libraries(test_tigervnc PRIVATE tigervnc::rfb)

enable_testing()
add_test(NAME consumer_api COMMAND test_tigervnc)
