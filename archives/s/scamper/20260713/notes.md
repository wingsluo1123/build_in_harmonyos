# scamper 20260713 adaptation notes

## Configuration

- Build the static measurement utility and helper libraries with select-based I/O.
- Disable privilege separation, io_uring, debug files, and upstream tests.
- Keep the portable trace, ping, DNS, HTTP, and UDP measurement modules enabled.

## Verification

- The consumer test executes `scamper -v` without raw-socket operations.
- Python syntax, recipe structure, source SHA-256, and whitespace are checked locally.
- The official OHOS armv8 pipeline remains authoritative for the full build result.
