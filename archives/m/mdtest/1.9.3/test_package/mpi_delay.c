#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static int wtime_calls;

double MPI_Wtime(void)
{
    int initialized = 0;
    int rank = -1;
    const char *rank_text;
    const char *call_text;
    const char *usec_text;

    PMPI_Initialized(&initialized);
    if (initialized) {
        PMPI_Comm_rank(MPI_COMM_WORLD, &rank);
        wtime_calls++;
        rank_text = getenv("MDTEST_DELAY_RANK");
        call_text = getenv("MDTEST_DELAY_WTIME_CALL");
        usec_text = getenv("MDTEST_DELAY_USEC");
        if (rank_text && call_text && usec_text &&
            rank == atoi(rank_text) && wtime_calls == atoi(call_text)) {
            unsigned long delay_usec = strtoul(usec_text, NULL, 10);
            fprintf(stderr,
                    "MDTEST_DELAY_APPLIED rank=%d wtime_call=%d usec=%lu\n",
                    rank, wtime_calls, delay_usec);
            fflush(stderr);
            usleep((useconds_t)delay_usec);
        }
    }
    return PMPI_Wtime();
}
