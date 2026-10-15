cmake_minimum_required(VERSION 3.15)
project(test_vector_blf CXX)

# Find the package through the Conan-generated CMakeDeps files.
find_package(vector-blf REQUIRED)
# The independent reference parser needs its own zlib (it must not link vector-blf).
find_package(ZLIB REQUIRED)

# Path of the packaged shared library, used by the OHOS ELF loadability probe.
# CMakeDeps exposes the package folder as <pkg>_PACKAGE_FOLDER_<CONFIG>; the
# aggregate conan target is INTERFACE, so $<TARGET_FILE:...> is not available.
if(DEFINED vector-blf_PACKAGE_FOLDER_RELEASE)
    set(VBLF_LIB_PATH "${vector-blf_PACKAGE_FOLDER_RELEASE}/lib/libVector_BLF.so")
else()
    set(VBLF_LIB_PATH "libVector_BLF.so")
endif()

# ── L1 consumer test (API round trip) ───────────────────────────────────────
add_executable(test_vector_blf test_vector_blf.cpp)
target_compile_features(test_vector_blf PRIVATE cxx_std_11)
target_link_libraries(test_vector_blf PRIVATE vector-blf::vector-blf)

# ── OHOS-specific end-to-end consumer case ──────────────────────────────────
add_executable(test_ohos_e2e test_ohos_e2e.cpp)
target_compile_features(test_ohos_e2e PRIVATE cxx_std_11)
target_link_libraries(test_ohos_e2e PRIVATE vector-blf::vector-blf)

# ── OHOS ELF loadability probe (deliberately NOT linked to vector-blf) ──────
add_executable(ohos_dlopen_probe ohos_dlopen_probe.cpp)
target_compile_features(ohos_dlopen_probe PRIVATE cxx_std_11)
target_link_libraries(ohos_dlopen_probe PRIVATE ${CMAKE_DL_LIBS})

# ── Independent reference implementation (deliberately NOT linked to vector-blf)
add_executable(ref_blf_parser ref_blf_parser.cpp)
target_compile_features(ref_blf_parser PRIVATE cxx_std_11)
target_link_libraries(ref_blf_parser PRIVATE ZLIB::ZLIB)

# ── Report cross-checker (enforces the container/compression invariants) ────
add_executable(test_compare test_compare.cpp)
target_compile_features(test_compare PRIVATE cxx_std_11)

set(E2E_BLF "${CMAKE_CURRENT_BINARY_DIR}/vector_blf_ohos_e2e.blf")
set(E2E_REPORT "${CMAKE_CURRENT_BINARY_DIR}/ohos_e2e.report")
set(E2E_REF_REPORT "${CMAKE_CURRENT_BINARY_DIR}/ohos_e2e_ref.report")

enable_testing()
add_test(NAME test_vector_blf COMMAND test_vector_blf)
add_test(NAME ohos_dlopen_probe COMMAND ohos_dlopen_probe "${VBLF_LIB_PATH}")

# End-to-end chain: consumer case -> independent parser -> cross-check.
add_test(NAME test_ohos_e2e COMMAND test_ohos_e2e "${E2E_REPORT}" "${E2E_BLF}")
add_test(NAME ref_blf_parser COMMAND ref_blf_parser "${E2E_BLF}" "${E2E_REF_REPORT}")
set_tests_properties(ref_blf_parser PROPERTIES DEPENDS test_ohos_e2e)
add_test(NAME test_compare COMMAND test_compare "${E2E_REPORT}" "${E2E_REF_REPORT}")
set_tests_properties(test_compare PROPERTIES DEPENDS "test_ohos_e2e;ref_blf_parser")
