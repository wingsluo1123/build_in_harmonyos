/* test_package/test.c — ARMCI API consumer test (R34: substantive test)
 *
 * This test calls armci-mpi API functions to verify the package is usable.
 * It follows the official ARMCI usage pattern:
 *   MPI_Init → ARMCI_Init → ARMCI_Malloc/Put/Get/Barrier → ARMCI_Finalize → MPI_Finalize
 *
 * Requires running with: mpiexec -n 2 ./test_armci_mpi
 */
#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include <armci.h>

#define DATA_NELTS 10
#define DATA_SZ (DATA_NELTS * sizeof(int))

int main(int argc, char **argv)
{
    int rank, nproc, i;
    int *buf;
    void **base_ptrs;
    int rc;

    MPI_Init(&argc, &argv);
    ARMCI_Init();

    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &nproc);

    if (rank == 0)
        printf("Starting ARMCI test_package with %d processes\n", nproc);

    buf = (int *)malloc(DATA_SZ);
    base_ptrs = (void **)malloc(sizeof(void *) * nproc);

    /* Allocate shared memory via ARMCI */
    rc = ARMCI_Malloc(base_ptrs, DATA_SZ);
    if (rc != 0) {
        fprintf(stderr, "rank %d: ARMCI_Malloc failed: %d\n", rank, rc);
        MPI_Abort(MPI_COMM_WORLD, 1);
    }

    /* Initialize local shared data */
    ARMCI_Access_begin(base_ptrs[rank]);
    for (i = 0; i < DATA_NELTS; i++)
        ((int *)base_ptrs[rank])[i] = rank * 100 + i;
    ARMCI_Access_end(base_ptrs[rank]);

    ARMCI_Barrier();

    /* Get data from neighbor (right) */
    {
        int neighbor = (rank + 1) % nproc;
        rc = ARMCI_Get(base_ptrs[neighbor], buf, DATA_SZ, neighbor);
        if (rc != 0) {
            fprintf(stderr, "rank %d: ARMCI_Get failed: %d\n", rank, rc);
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
        /* Verify received data */
        for (i = 0; i < DATA_NELTS; i++) {
            int expected = neighbor * 100 + i;
            if (buf[i] != expected) {
                fprintf(stderr, "rank %d: GET expected %d, got %d\n", rank, expected, buf[i]);
                MPI_Abort(MPI_COMM_WORLD, 1);
            }
        }
    }

    ARMCI_Barrier();

    /* Put data to neighbor (left) */
    {
        int neighbor = (rank + nproc - 1) % nproc;
        for (i = 0; i < DATA_NELTS; i++)
            buf[i] = rank * 200 + i;
        rc = ARMCI_Put(buf, base_ptrs[neighbor], DATA_SZ, neighbor);
        if (rc != 0) {
            fprintf(stderr, "rank %d: ARMCI_Put failed: %d\n", rank, rc);
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
    }

    ARMCI_Barrier();

    /* Verify put data was received */
    ARMCI_Access_begin(base_ptrs[rank]);
    {
        int putter = (rank + 1) % nproc;
        for (i = 0; i < DATA_NELTS; i++) {
            int expected = putter * 200 + i;
            if (((int *)base_ptrs[rank])[i] != expected) {
                fprintf(stderr, "rank %d: PUT expected %d, got %d\n",
                        rank, expected, ((int *)base_ptrs[rank])[i]);
                MPI_Abort(MPI_COMM_WORLD, 1);
            }
        }
    }
    ARMCI_Access_end(base_ptrs[rank]);

    ARMCI_Free(base_ptrs[rank]);
    free(base_ptrs);
    free(buf);

    ARMCI_Finalize();
    MPI_Finalize();

    if (rank == 0)
        printf("ARMCI test_package: PASS (Malloc/Get/Put/Barrier/Free OK)\n");

    return 0;
}
