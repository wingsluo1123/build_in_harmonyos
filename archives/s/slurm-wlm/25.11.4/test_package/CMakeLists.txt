cmake_minimum_required(VERSION 3.15)
project(slurm_consumer C)

find_package(Slurm REQUIRED)

add_executable(test_slurm test_slurm.c)
target_link_libraries(test_slurm PRIVATE "${SLURM_LIBRARY}")
# make the include path explicit: consumers do #include <slurm/slurm.h>
target_include_directories(test_slurm PRIVATE "${SLURM_INCLUDE_DIR}")
