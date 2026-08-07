cmake_minimum_required(VERSION 3.15)
project(test_postgresql_orafce C)

# Find the package via Conan-generated CMakeDeps
find_package(postgresql-orafce REQUIRED)

add_executable(test_postgresql_orafce test.c)
target_link_libraries(test_postgresql_orafce ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_postgresql_orafce
         COMMAND test_postgresql_orafce
                 $<TARGET_FILE:postgresql-orafce::postgresql-orafce>)
