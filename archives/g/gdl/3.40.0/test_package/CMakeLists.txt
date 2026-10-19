cmake_minimum_required(VERSION 3.15)
project(test_gdl C)

find_package(PkgConfig REQUIRED)

# Consume the installed gdl-3.0.pc (Requires: gtk+-3.0 propagates the
# transitive pango/gdk-pixbuf include/lib paths; Requires.private:
# libxml-2.0 pulls the XML parser — pkg_check_modules resolves the chain,
# avoiding the CMakeDeps component-header breakage — E216).
pkg_check_modules(GDL REQUIRED gdl-3.0 IMPORTED_TARGET)

# Version gate: the .pc Version field must carry the recipe version.
if(NOT GDL_VERSION VERSION_EQUAL 3.40.0)
    message(FATAL_ERROR "gdl-3.0.pc version mismatch: got '${GDL_VERSION}', expected 3.40.0")
endif()
message(STATUS "gdl-3.0.pc version: ${GDL_VERSION} (ok)")

add_executable(test_gdl test.c)
target_include_directories(test_gdl PRIVATE ${GDL_INCLUDE_DIRS})
target_link_directories(test_gdl PRIVATE ${GDL_LIBRARY_DIRS})
target_link_libraries(test_gdl PRIVATE ${GDL_LIBRARIES})
target_compile_options(test_gdl PRIVATE ${GDL_CFLAGS_OTHER})
