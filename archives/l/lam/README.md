# lam — LAM/MPI (Local Area Multicomputer)

LAM/MPI 7.1.4 is an MPI (Message Passing Interface) implementation for
cluster and multi-core systems. It provides `liblam`, `libmpi` and
`liblammpi++` (C++ bindings), the `lamd` local daemon, and a tool set
(`lamboot`, `laminfo`, `mpirun`, `lamhalt`, `lamgrow`, `lamshrink`, ...)
built on the SSI (System Services Interface) module architecture.

Upstream: https://www.lam-mpi.org/ (development ended in 2007; source
taken from the Debian pool archive).

## Build system

Autotools (autoconf 2.59 generated configure, bundled libltdl,
2007-07-22 config.guess/config.sub, 23+ SSI module sub-configures).

## OHOS adaptation

- `config.guess`/`config.sub` (all 23 byte-identical copies) patched with
  a HarmonyOS branch; the canonical `config/` copies are propagated to
  the remaining 22 copies programmatically by the conanfile.
- `configure` is invoked explicitly through the shell (the conan cache
  filesystem does not preserve exec bits) with `SHELL=/bin/sh`; patch
  0004 rewrites the 6 top-level `cmd="$libtool ..."` probe sites to
  `cmd="$SHELL $libtool ..."` for the same reason.
- `RSH_COMMAND=/usr/bin/ssh` is preset so the rsh boot module always
  configures (documented override of that module's configure).
- The PMPI stub rules and the wrapper install-exec-hook hard-code
  `ln -s`; the conanfile rewrites them to the equivalent `cp -p`
  / direct symlink target after configure (no behavioural difference
  on systems with working symlinks).
- Serial `make` (the build filesystem rejects the mkfifo jobserver used
  by `make -j`); a full build takes ~25 min, within the default CI
  timeout.
- Consumers must compile against `cpp_info` flags directly
  (`-llammpi++ -lmpi -llam -ldl`, `_REENTRANT`): LAM's own hcc/mpicc
  wrapper binaries do not work on OHOS.
- Tools resolve their etc/ files (schema, bhost, helpfile) through the
  `LAMHOME` environment variable, injected by `package_info`.

## Known limitations

- Fortran bindings not built (`--without-fc`).
- ROMIO / MPI-IO not built (`--without-romio`).
- Static libraries only (tested configuration).
- Upstream tests: 18 cases = 15 pass / 0 fail / 3 skip (Fortran).

## License

BSD-style license (see LICENSE shipped with the source tarball).
