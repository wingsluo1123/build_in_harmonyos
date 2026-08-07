# Test Report — pure-ftpd 1.0.52-r0

## Build Test

- **Build system**: autotools
- **Configure**: ./configure --disable-dependency-tracking --with-everything --with-tls ...
- **Make**: make -j1 (passed)
- **Make install**: make install DESTDIR=... (passed)
- **Make check**: make check (passed, no test cases)

## Smoke Test

- `pure-ftpd --help`: shows all command-line options ✓
- `pure-pw --help`: shows usage ✓

## Conan Verification

- conan-verify: PASSED (G1, G0, G2, G3, G4)
- conan create: PASSED
- W3 local CI simulation: PASSED

## Binary List

| Binary | Path | Size |
|--------|------|------|
| pure-ftpd | sbin/ | 2.7MB |
| pure-ftpwho | sbin/ | 68KB |
| pure-authd | sbin/ | 35KB |
| pure-certd | sbin/ | 31KB |
| pure-mrtginfo | sbin/ | 23KB |
| pure-quotacheck | sbin/ | 31KB |
| pure-uploadscript | sbin/ | 31KB |
| pure-pw | bin/ | 52KB |
| pure-pwconvert | bin/ | 23KB |
| pure-statsdecode | bin/ | 23KB |

## Status

All tests passed. Package is ready for submission.
