cmake_minimum_required(VERSION 3.15)
project(test_vfs_libarchive LANGUAGES CXX)

# Resolve through Conan CMakeDeps, same as any downstream Kodi deployment
# tooling; cmake_file_name is "kodi-vfs-libarchive".
find_package(kodi-vfs-libarchive CONFIG REQUIRED)
# Explicit direct require of the module's libarchive closure: the test binary
# links it for the in-process functional smoke (the "indirect dependency
# INCLUDE_DIRS are empty" trap from kodi-platform/20250416 notes is avoided by
# this explicit require).
find_package(libarchive CONFIG REQUIRED)

add_executable(test_vfs_libarchive test_vfs_libarchive.cpp)
target_compile_features(test_vfs_libarchive PRIVATE cxx_std_17)
target_link_libraries(test_vfs_libarchive PRIVATE
                      ${CMAKE_DL_LIBS}
                      libarchive::archive)

enable_testing()
add_test(NAME vfs_libarchive_addon_entry_points
         COMMAND test_vfs_libarchive ${ADDON_LIB_DIR}/vfs.libarchive.so)
