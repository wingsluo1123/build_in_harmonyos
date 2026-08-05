cmake_minimum_required(VERSION 3.15)
project(test_aws_c_auth C)

find_package(aws-c-auth REQUIRED)
find_package(aws-c-common REQUIRED)
find_package(aws-c-cal REQUIRED)
find_package(aws-c-sdkutils REQUIRED)
find_package(aws-c-io REQUIRED)
find_package(aws-c-http REQUIRED)
find_package(aws-c-compression REQUIRED)
find_package(aws-lc REQUIRED)

add_executable(test_aws-c-auth test.c stub.c)

# Export dynamic symbols from executable so shared libraries can resolve
# aws_tls_handler_protocol from our stub.c
target_link_options(test_aws-c-auth PRIVATE -Wl,--export-dynamic)

# Allow undefined symbols in shared libraries (aws-c-io built with BYO_CRYPTO
# excludes aws_tls_handler_protocol which aws-c-http references)
target_link_options(test_aws-c-auth PRIVATE -Wl,--allow-shlib-undefined)

target_link_libraries(test_aws-c-auth
    aws-c-auth::aws-c-auth
    aws-c-common::aws-c-common
    aws-c-cal::aws-c-cal
    aws-c-sdkutils::aws-c-sdkutils
    aws-c-io::aws-c-io
    aws-c-http::aws-c-http
    aws-c-compression::aws-c-compression
    aws-lc::aws-lc
)

# Fallback: CMakeDeps stubs may have empty LIBS and INCLUDE_DIRS.
# Use find_path/find_library to locate them manually.
find_path(AWS_COMMON_INCLUDE_DIR aws/common/common.h)
find_library(AWS_COMMON_LIB aws-c-common)
find_path(AWS_AUTH_INCLUDE_DIR aws/auth/auth.h)
find_library(AWS_AUTH_LIB aws-c-auth)
find_library(AWS_CRYPTO_LIB crypto)

if(AWS_COMMON_INCLUDE_DIR)
    target_include_directories(test_aws-c-auth PRIVATE ${AWS_COMMON_INCLUDE_DIR})
endif()
if(AWS_AUTH_INCLUDE_DIR)
    target_include_directories(test_aws-c-auth PRIVATE ${AWS_AUTH_INCLUDE_DIR})
endif()
if(AWS_COMMON_LIB)
    target_link_libraries(test_aws-c-auth ${AWS_COMMON_LIB})
endif()
if(AWS_AUTH_LIB)
    target_link_libraries(test_aws-c-auth ${AWS_AUTH_LIB})
endif()
if(AWS_CRYPTO_LIB)
    target_link_libraries(test_aws-c-auth ${AWS_CRYPTO_LIB})
endif()

enable_testing()
add_test(NAME test_aws_c_auth COMMAND test_aws-c-auth)
