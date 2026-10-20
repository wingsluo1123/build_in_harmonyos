cmake_minimum_required(VERSION 3.15)
project(test_libest C)

# Find the package via Conan-generated CMakeDeps
find_package(libest REQUIRED)
# libest's public header (est.h) includes <openssl/ssl.h>, so the consumer
# must also resolve OpenSSL headers/libs.
find_package(OpenSSL REQUIRED)

# The openssl package in the OHOS conan cache does not export its
# include dir through CMakeDeps metadata, so add the packaged header dir
# explicitly (headers are shipped in the package include/ folder).
if(DEFINED openssl_PACKAGE_FOLDER_RELEASE)
    include_directories("${openssl_PACKAGE_FOLDER_RELEASE}/include")
elseif(DEFINED openssl_PACKAGE_FOLDER)
    include_directories("${openssl_PACKAGE_FOLDER}/include")
endif()

add_executable(test_libest test.c)
# Link with all OpenSSL targets to carry headers/libs transitively.
target_link_libraries(test_libest
    libest::libest
    OpenSSL::SSL
    OpenSSL::Crypto
    openssl::openssl
)

enable_testing()
add_test(NAME test_libest COMMAND test_libest)
