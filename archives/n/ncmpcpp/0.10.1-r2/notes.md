# ncmpcpp 0.10.1-r2 adaptation notes

## Configuration

- Regenerate the release build files with `autoreconf` and use the OHOS cross compiler through Conan AutotoolsToolchain.
- Enable clock, outputs, visualizer, FFTW, ICU, and TagLib support.
- Disable LTO to avoid cross-linker plugin coupling.

## Verification

- The consumer test executes `ncmpcpp --version` without an MPD server.
- Python syntax, recipe structure, source SHA-256, and whitespace are checked locally.
- The official OHOS armv8 pipeline remains authoritative for the full build result.
