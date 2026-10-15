# LIKWID (likwid)

LIKWID is the HPC performance analysis tool suite from RRZE (University of
Erlangen-Nuremberg).  It ships the `liblikwid` C library, a Lua binding and a
set of command line tools (`likwid-perfctr`, `likwid-topology`, `likwid-pin`,
`likwid-bench`, `likwid-powermeter`, `likwid-memsweeper`, ...).

## OHOS adaptation

- Built with the upstream Makefile, `COMPILER=CLANGARMv8` and
  `ACCESSMODE=perf_event` (so no msr access daemon is required).  hwloc 2.9.3
  and Lua 5.4 are built from the bundled sources (upstream default).
- Three portability patches cover the OHOS/bionic gaps: glibc-only
  `pthread_[sg]etaffinity_np` / `__cpu_mask` / `program_invocation_name`,
  hwloc's sysfs sibling-file probe (OHOS exposes `*_list` files), the missing
  Package/Socket object, and the `get_mempolicy` seccomp SIGSYS trap.
- The recipe provides two build shims because OHOS ships neither the `cpp`
  driver used by likwid-bench's perl generator nor coreutils `install`.

## Runtime scope on OHOS

OHOS denies `perf_event_open` (EACCES) and exposes no `/dev/cpu/*/msr`, so
hardware counter *measurement* (`likwid-perfctr`, `likwid-powermeter`) cannot
run here.  Topology discovery, NUMA enumeration, thread affinity, the cycle
timer and process pinning are fully functional and exercised by the consumer
test.

## Usage

```sh
eval "$(conanbuildinfo ...)"   # or set LD_LIBRARY_PATH / PATH to the package
likwid-topology -c
likwid-pin -c 0 ./my_program
```

Link against the library with `-llikwid` and `#include <likwid.h>`.
