cmake_minimum_required(VERSION 3.15)
project(test_libxtrxdsp C)

# Package discovery is provided by the Conan-generated CMakeDeps files
# (find_package(libxtrxdsp) + libxtrxdsp::libxtrxdsp).
find_package(libxtrxdsp REQUIRED)

# Consumer integration test: public conversion and FIR filter API with
# deterministic expected values.  No hardware, no device node.
add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer PRIVATE libxtrxdsp::libxtrxdsp)

# HarmonyOS-specific test: packaged symbol set, aarch64 code path selection,
# byte order assumption and filter allocation cycles.
add_executable(test_ohos_dsp test_ohos_dsp.c)
target_link_libraries(test_ohos_dsp PRIVATE libxtrxdsp::libxtrxdsp ${CMAKE_DL_LIBS})
