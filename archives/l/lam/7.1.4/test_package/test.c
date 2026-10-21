#include <mpi.h>
#include <stdio.h>

/* HarmonyOS consumer smoke test for LAM/MPI 7.1.4.
 * Deliberately does NOT use assert(): assertions compile out under NDEBUG.
 * The Allreduce sum is verified with an explicit branch and the verifiable
 * marker LAM-SMOKE-OK is printed on success. */
int main(int argc, char **argv)
{
    int rank = -1;
    int size = 0;
    int value = 0;
    int sum = 0;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    value = rank + 1;
    MPI_Allreduce(&value, &sum, 1, MPI_INT, MPI_SUM, MPI_COMM_WORLD);

    if (rank == 0) {
        int expected = size * (size + 1) / 2;
        if (sum != expected) {
            fprintf(stderr, "LAM-SMOKE-FAIL: MPI_Allreduce returned %d, expected %d\n",
                    sum, expected);
            MPI_Abort(MPI_COMM_WORLD, 2);
        }
        printf("LAM-SMOKE-OK: rank %d of %d, allreduce sum %d\n", rank, size, sum);
        fflush(stdout);
    }

    MPI_Finalize();
    return 0;
}
