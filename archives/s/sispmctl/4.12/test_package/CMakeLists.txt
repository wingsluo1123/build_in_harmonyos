cmake_minimum_required(VERSION 3.15)
project(test_sispmctl C)

# Consumer test for the sispmctl package: link the real libsispmctl (which
# statically pulls in the libusb-0.1 compat layer and libusb-1.0) and run
# the pure schedule API round-trip as a single ctest case.
find_package(sispmctl CONFIG REQUIRED)
find_package(libusb-compat CONFIG REQUIRED)
find_package(libusb-1.0 CONFIG REQUIRED)

# sispmctl's upstream Makefile.am installs no public header; the main recipe
# copies src/sispm_ctl.h into <pkg>/include and the test recipe injects that
# path here via SISPMCTL_INCLUDE_DIR at configure time. It also does NOT
# install any import lib through the CMakeDeps consumer target for this
# application-package type (see test_package/conanfile.py build()), so the real
# static archive is injected as SISPMCTL_LIBRARY and linked explicitly.
# Guard loudly so a missing/empty injection cannot silently produce an empty
# include path or an archive-less link.
if(NOT DEFINED SISPMCTL_INCLUDE_DIR OR NOT EXISTS "${SISPMCTL_INCLUDE_DIR}/sispm_ctl.h")
    message(FATAL_ERROR
        "SISPMCTL_INCLUDE_DIR not provided or does not contain sispm_ctl.h: "
        "${SISPMCTL_INCLUDE_DIR}")
endif()
if(NOT DEFINED SISPMCTL_LIBRARY OR NOT EXISTS "${SISPMCTL_LIBRARY}")
    message(FATAL_ERROR
        "SISPMCTL_LIBRARY not provided or does not exist: "
        "${SISPMCTL_LIBRARY}")
endif()

add_executable(test_sispmctl test_sispmctl.c)
target_include_directories(test_sispmctl PRIVATE "${SISPMCTL_INCLUDE_DIR}")
target_link_libraries(test_sispmctl PRIVATE
    "${SISPMCTL_LIBRARY}"
    libusb-compat::libusb-compat
    libusb-1.0::libusb-1.0
)

include(CTest)
if(BUILD_TESTING)
    add_test(NAME test_sispmctl COMMAND test_sispmctl)
endif()
