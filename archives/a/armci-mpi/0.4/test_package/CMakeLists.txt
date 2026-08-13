cmake_minimum_required(VERSION 3.15)
project(test_armci_mpi C)

# Find armci-mpi package
find_package(armci-mpi REQUIRED)
# Find MPI (transitive dependency from mpich)
find_package(MPI REQUIRED)

add_executable(test_armci_mpi test.c)
target_link_libraries(test_armci_mpi armci-mpi::armci-mpi MPI::MPI_C)

enable_testing()
add_test(NAME test_armci_mpi COMMAND ${MPIEXEC_EXECUTABLE} ${MPIEXEC_NUMPROC_FLAG} 2 ./test_armci_mpi)
