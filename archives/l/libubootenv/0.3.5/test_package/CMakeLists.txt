cmake_minimum_required(VERSION 3.5)
project(test_ubootenv C)

find_package(libubootenv REQUIRED CONFIG)

# Consumer API test: link against the package and exercise the API
add_executable(test_ubootenv test_ubootenv.c)
target_link_libraries(test_ubootenv PRIVATE libubootenv::libubootenv)

# OHOS-specific runtime test: dlopen the shared library to verify
# SONAME correctness and transitive dependency resolvability
add_executable(test_dlopen test_dlopen.c)
target_link_libraries(test_dlopen PRIVATE libubootenv::libubootenv)
