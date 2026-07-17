# SCOTCH 7.0.12 adaptation notes

## Configuration

- Build the threaded static graph-partitioning libraries with zlib, bzip2, and LZMA input support.
- Disable Fortran, MPI/PT-SCOTCH, EsMUMPS, METIS compatibility, and upstream tests.
- Use the portable C library interfaces on HarmonyOS PC.

## Verification

- The consumer test calls `SCOTCH_version` and checks all version components.
- Python syntax, recipe structure, source SHA-256, and whitespace are checked locally.
- The official OHOS armv8 pipeline remains authoritative for the full build result.
