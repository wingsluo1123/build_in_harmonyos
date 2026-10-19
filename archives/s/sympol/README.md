# SymPol

SymPol 0.1.9 converts polyhedral descriptions up to symmetry.

## OHOS adaptation

The public library is shared. Its private bundled lrs/cdd implementation
engines are static/PIC. Preserve the literal loader token in the generated
CMake toolchain; passing it through a double-quoted cache argument can strip
it before link. Public header subdirectory layout is retained.

## Dependencies

GMP 6.3.0.1, Boost 1.91.0.1.4 and PermLib 0.2.9 must be released first.
Optional Eigen and Bliss backends are not enabled in this configuration.

## Validation

See 0.1.9/reports/test-report.md for the 30/30 upstream and 4/4 installed
shared-consumer native W3 result. Formal finish, Pre-PR, review and CI remain
pending.
