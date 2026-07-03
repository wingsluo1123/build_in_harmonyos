cmake_minimum_required(VERSION 3.15)
project(test_perl-package-stash-xs C)

# Find the package via Conan-generated CMakeDeps
find_package(perl-package-stash-xs REQUIRED)

add_executable(test_perl-package-stash-xs test.c)
target_link_libraries(test_perl-package-stash-xs perl-package-stash-xs::perl-package-stash-xs)

enable_testing()
add_test(NAME test_perl-package-stash-xs COMMAND test_perl-package-stash-xs)
