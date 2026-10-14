cmake_minimum_required(VERSION 3.15)
project(test_inputstream_adaptive LANGUAGES CXX)

# Resolve through Conan CMakeDeps, same as any downstream consumer of the
# packaged add-on module.
find_package(kodi-inputstream-adaptive CONFIG REQUIRED)

add_executable(test_inputstream_adaptive test_inputstream_adaptive.cpp)
target_compile_features(test_inputstream_adaptive PRIVATE cxx_std_17)
target_link_libraries(test_inputstream_adaptive PRIVATE
                      kodi-inputstream-adaptive::kodi-inputstream-adaptive
                      ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_inputstream_adaptive COMMAND test_inputstream_adaptive)
