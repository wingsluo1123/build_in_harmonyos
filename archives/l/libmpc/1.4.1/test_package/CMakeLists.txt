cmake_minimum_required(VERSION 3.15)
project(test_libmpc C)

# Find the package via Conan-generated CMakeDeps
find_package(libmpc REQUIRED)

# GMP and MPFR are system libraries (not Conan packages).
# Locate them explicitly so the test can link.
find_library(GMP_LIB gmp
    PATHS /storage/Users/currentUser/.harmonybrew/Cellar/gmp/6.3.0/lib
    NO_DEFAULT_PATH)
find_library(MPFR_LIB mpfr
    PATHS /storage/Users/currentUser/.harmonybrew/Cellar/mpfr/4.2.2/lib
    NO_DEFAULT_PATH)

add_executable(test_libmpc test.c)
target_link_libraries(test_libmpc libmpc::libmpc ${GMP_LIB} ${MPFR_LIB})

# Include paths for GMP and MPFR headers (mpc.h includes gmp.h and mpfr.h)
target_include_directories(test_libmpc PRIVATE
    /storage/Users/currentUser/.harmonybrew/Cellar/gmp/6.3.0/include
    /storage/Users/currentUser/.harmonybrew/Cellar/mpfr/4.2.2/include
)

enable_testing()
add_test(NAME test_libmpc COMMAND test_libmpc)
