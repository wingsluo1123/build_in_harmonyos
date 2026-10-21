cmake_minimum_required(VERSION 3.15)
project(test_odb CXX)
find_package(odb REQUIRED)
add_executable(test_odb test.cpp)
target_link_libraries(test_odb odb::odb)

# The downloaded sqlite3/3.49.1 registry dependency exports no include
# directories through CMakeDeps (empty INTERFACE_INCLUDE_DIRECTORIES),
# while <odb/sqlite/database.hxx> includes <sqlite3.h> unconditionally.
# The test conanfile passes the dependency package's include dir here
# through CMakeToolchain (SQLITE3_INCLUDE_DIR).
if(SQLITE3_INCLUDE_DIR)
    target_include_directories(test_odb PRIVATE "${SQLITE3_INCLUDE_DIR}")
endif()
