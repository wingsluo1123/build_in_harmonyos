cmake_minimum_required(VERSION 3.28)

project(test_obs C)

# Conan's CMakeDeps provides the package under its cmake_file_name ("libobs")
# exporting the OBS::libobs target.
find_package(libobs CONFIG REQUIRED)

add_executable(test_obs src/test_obs.c)
target_link_libraries(test_obs PRIVATE OBS::libobs)
