cmake_minimum_required(VERSION 3.15)
project(test_rpki_client C)

# RPKI_CLIENT_BIN is passed by conanfile.py test() — absolute path to rpki-client binary
set(RPKI_CLIENT_BIN "rpki-client" CACHE STRING "Path to rpki-client binary")

add_executable(test_rpki_client test.c)

enable_testing()
add_test(NAME test_rpki_client COMMAND test_rpki_client)
# Pass RPKI_CLIENT_PATH to the test binary via CTest environment
set_tests_properties(test_rpki_client PROPERTIES
    ENVIRONMENT "RPKI_CLIENT_PATH=${RPKI_CLIENT_BIN}"
)
