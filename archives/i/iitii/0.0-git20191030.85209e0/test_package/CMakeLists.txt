cmake_minimum_required(VERSION 3.15)
project(test_iitii CXX)

find_package(iitii REQUIRED)
find_package(Catch2 REQUIRED)

add_executable(test_iitii test_iitii.cpp)
target_link_libraries(test_iitii PRIVATE iitii::iitii)
target_compile_features(test_iitii PRIVATE cxx_std_14)

# OHOS-adapted upstream suite: test/test_iitii.cc ported to the mm_builder
# API (backing files), without htslib/CTPL/jemalloc (see upstream_test_iitii.cc
# header). Catch2 comes from the Conan test dependency (catch2/2.13.10)
# instead of the upstream ExternalProject Catch v2.9.1.zip download.
add_executable(upstream_test_iitii upstream_test_iitii.cc)
target_link_libraries(upstream_test_iitii PRIVATE iitii::iitii Catch2::Catch2)
target_compile_features(upstream_test_iitii PRIVATE cxx_std_17)

# Deliberately NO OpenMP linkage: HarmonyOS provides no OpenMP runtime
# (libomp), so src/iitii.h is patched (conandata 0001) to a single-threaded
# builder + serial ips4o::sort when _OPENMP is undefined. Linking
# OpenMP::OpenMP_CXX here would add a libomp.so NEEDED entry that the OHOS
# loader cannot resolve at test runtime.
enable_testing()
add_test(NAME test_iitii COMMAND test_iitii)
add_test(NAME unit_tests COMMAND upstream_test_iitii)
