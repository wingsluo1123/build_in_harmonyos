/* Consumer test for the LIKWID C API on OHOS.
 *
 * Exercises the parts of the public API that are meaningful on a machine
 * without a usable performance-counter backend (OHOS denies perf_event_open
 * and exposes no CPU msr device): topology discovery, NUMA (virtual node),
 * thread affinity, the cycle timer, cpu-string parsing and process pinning.
 */
#include <likwid.h>

#include <sched.h>
#include <stdio.h>

static int failures = 0;

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (cond) {                                                            \
            printf("ok   : %s\n", msg);                                        \
        } else {                                                               \
            printf("FAIL : %s\n", msg);                                        \
            failures++;                                                        \
        }                                                                      \
    } while (0)

int main(void)
{
    int cpus[8];

    topology_init();
    CpuTopology_t topo = get_cpuTopology();
    CpuInfo_t info = get_cpuInfo();
    CHECK(topo != NULL, "get_cpuTopology() non-NULL");
    CHECK(info != NULL, "get_cpuInfo() non-NULL");
    if (topo != NULL) {
        CHECK(topo->numHWThreads > 0, "numHWThreads > 0");
        CHECK(topo->numSockets > 0, "numSockets > 0");
        CHECK(topo->numThreadsPerCore >= 1, "numThreadsPerCore >= 1");
    }
    if (info != NULL) {
        CHECK(info->osname != NULL && info->osname[0] != '\0',
              "cpuInfo osname non-empty");
        if (topo != NULL) {
            printf("     : CPU=%s hwthreads=%d sockets=%d threads/core=%d\n",
                   info->osname, topo->numHWThreads, topo->numSockets,
                   topo->numThreadsPerCore);
        }
    }

    timer_init();
    CHECK(timer_getCpuClock() > 0, "timer_getCpuClock() > 0");
    timer_finalize();

    numa_init();
    CHECK(likwid_getNumberOfNodes() >= 1, "numa nodes >= 1");
    numa_finalize();

    affinity_init();
    AffinityDomains_t doms = get_affinityDomains();
    CHECK(doms != NULL && doms->numberOfAffinityDomains > 0,
          "affinity domains > 0");
    affinity_finalize();

    int n = cpustr_to_cpulist("0,1", cpus, 8);
    CHECK(n == 2, "cpustr_to_cpulist(\"0,1\") == 2");

    /* likwid_pinProcess() returns TRUE (1) on success. */
    CHECK(likwid_pinProcess(0) != 0, "likwid_pinProcess(0) ok");

    topology_finalize();

    printf("consumer_failures=%d\n", failures);
    return failures == 0 ? 0 : 1;
}
