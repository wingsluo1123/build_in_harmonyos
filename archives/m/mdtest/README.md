# mdtest

mdtest is an MPI-coordinated benchmark for parallel filesystem metadata operations.

The HarmonyOS PC package installs the `mdtest` command and uses the published MPICH runtime. Run it through `mpiexec`, for example:

```sh
mpiexec -n 4 mdtest -d /data/storage/el2/base/cache/mdtest-run -n 100 -i 3
```

Version `1.9.3` preserves the upstream command-line surface and corrects barrier-mode aggregation so reported throughput follows the slowest rank's completion time.
