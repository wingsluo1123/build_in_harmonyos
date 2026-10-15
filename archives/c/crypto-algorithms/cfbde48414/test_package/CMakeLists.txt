cmake_minimum_required(VERSION 3.15)
project(test_crypto-algorithms C)

# Find the package via Conan-generated CMakeDeps
find_package(crypto-algorithms CONFIG REQUIRED)

# Source-redistribution package: consumers compile the algorithm .c files
# they need. Locate the packaged sha256.c inside the include dirs.
find_file(CRYPTO_SHA256_SOURCE
    NAMES sha256.c
    PATHS ${crypto-algorithms_INCLUDE_DIRS}
    NO_DEFAULT_PATH
    REQUIRED
)

add_executable(test_crypto-algorithms test.c ${CRYPTO_SHA256_SOURCE})
target_link_libraries(test_crypto-algorithms PRIVATE crypto-algorithms::crypto-algorithms)
set_property(TARGET test_crypto-algorithms PROPERTY C_STANDARD 99)

enable_testing()
add_test(NAME test_crypto-algorithms COMMAND test_crypto-algorithms)
