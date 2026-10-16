# rdma (rdma-core)

RDMA core userspace libraries and daemons for the Linux InfiniBand/RDMA subsystem.
归档名 `rdma` 取自上游 `CMakeLists.txt` 的 `set(PACKAGE_NAME "RDMA")`。

Provides:
- **libibverbs** — RDMA verbs API
- **librdmacm** — RDMA connection manager
- **libibumad** — InfiniBand MAD library
- **libibmad** — InfiniBand MAD library
- **libibnetdisc** — InfiniBand fabric discovery
- **infiniband-diags** — diagnostic tools
- **daemons** — ibacm, iwpmd, srp_daemon, rdma-ndd

## OHOS Adaptation

Optional features disabled for HarmonyOS PC:
- `ENABLE_RESOLVE_NEIGH=0` — no libnl dependency
- `NO_PYVERBS=1` — no Python bindings (Cython + numpy not available in CI)
- `NO_MAN_PAGES=1` — no man pages (pandoc)
- `NO_COMPAT_SYMS=1` — no GNU symbol versioning (musl libc)
- `ENABLE_VALGRIND=0` — no valgrind annotations

Recipe-level portability flags and a single compat header
(`compat/ohos-compat.h`) close the OHOS libc gaps; only one upstream
source patch is applied (rping thread teardown, knowledge E513).
See `64.0/notes.md` and `64.0/reports/test-report.md`.

## Source

- Homepage: https://github.com/linux-rdma/rdma-core
- License: GPL-2.0 OR BSD-2-Clause
