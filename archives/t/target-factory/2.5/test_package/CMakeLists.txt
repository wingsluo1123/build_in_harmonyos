cmake_minimum_required(VERSION 3.15)
project(test_target_factory CXX)

# protobuf's registry package is cmake_find_mode=none: CMakeDeps generates no
# config for it, while target-factory's public header includes the generated
# target.pb.h.  Load protobuf's own installed config (protobuf_DIR injected
# via conan_toolchain) before target-factory.
find_package(Protobuf CONFIG REQUIRED)

find_package(target-factory REQUIRED CONFIG)

add_executable(test_target_factory test_target_factory.cpp)
target_link_libraries(test_target_factory PRIVATE
    target-factory::target-factory
    protobuf::libprotobuf)
target_compile_features(test_target_factory PRIVATE cxx_std_17)
set_target_properties(test_target_factory PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")

enable_testing()
add_test(NAME test_target_factory COMMAND test_target_factory)
