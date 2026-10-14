#include <hdf5.h>
#include <mpi.h>
#include <stdio.h>
#include <unistd.h>

#define CHECK(expr) do { if (!(expr)) { \
  fprintf(stderr, "consumer failure line %d: %s\n", __LINE__, #expr); \
  MPI_Abort(MPI_COMM_WORLD, 1); return 1; } } while (0)

int main(int argc, char **argv)
{
  int rank, size;
  if (MPI_Init(&argc, &argv) != MPI_SUCCESS) {
    fputs("MPI_Init failed\n", stderr);
    return 1;
  }
  CHECK(MPI_Comm_rank(MPI_COMM_WORLD, &rank) == MPI_SUCCESS);
  CHECK(MPI_Comm_size(MPI_COMM_WORLD, &size) == MPI_SUCCESS);
  CHECK(size == 2);
  hid_t access = H5Pcreate(H5P_FILE_ACCESS);
  CHECK(access >= 0);
  CHECK(H5Pset_fapl_mpio(access, MPI_COMM_WORLD, MPI_INFO_NULL) >= 0);
  hid_t file = H5Fcreate("real-consumer-two-rank.h5", H5F_ACC_TRUNC,
                        H5P_DEFAULT, access);
  CHECK(file >= 0);
  hsize_t dims[1] = {2};
  hid_t space = H5Screate_simple(1, dims, NULL);
  CHECK(space >= 0);
  hid_t dataset = H5Dcreate2(file, "values", H5T_NATIVE_INT, space,
                            H5P_DEFAULT, H5P_DEFAULT, H5P_DEFAULT);
  CHECK(dataset >= 0);
  int written[2] = {19, 23}, restored[2] = {0, 0};
  if (rank == 0)
    CHECK(H5Dwrite(dataset, H5T_NATIVE_INT, H5S_ALL, H5S_ALL,
                   H5P_DEFAULT, written) >= 0);
  CHECK(MPI_Barrier(MPI_COMM_WORLD) == MPI_SUCCESS);
  CHECK(H5Dread(dataset, H5T_NATIVE_INT, H5S_ALL, H5S_ALL,
                H5P_DEFAULT, restored) >= 0);
  CHECK(restored[0] == 19 && restored[1] == 23);
  CHECK(H5Dclose(dataset) >= 0);
  CHECK(H5Sclose(space) >= 0);
  CHECK(H5Fclose(file) >= 0);
  CHECK(H5Pclose(access) >= 0);
  CHECK(MPI_Barrier(MPI_COMM_WORLD) == MPI_SUCCESS);
  if (rank == 0) {
    CHECK(unlink("real-consumer-two-rank.h5") == 0);
    puts("REAL_MPI_HDF5_CONSUMER_PASS=1/1");
  }
  if (MPI_Finalize() != MPI_SUCCESS) {
    fputs("MPI_Finalize failed\n", stderr);
    return 1;
  }
  return 0;
}
