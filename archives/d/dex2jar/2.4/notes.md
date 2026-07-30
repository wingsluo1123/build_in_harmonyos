# dex2jar 2.4 — Adaptation Notes

## Overview

- **Project**: dex2jar
- **Version**: 2.4
- **Homepage**: https://github.com/pxb1988/dex2jar
- **Source**: https://github.com/pxb1988/dex2jar/archive/refs/tags/v2.4.tar.gz
- **License**: Apache-2.0
- **Description**: Tools to convert Android .dex files to .class files (JAR)
- **Build system**: Custom (Gradle)
- **Package type**: application

## Source Acquisition

The source tarball is fetched from the official GitHub release tag. After first
download, compute the SHA-256 and add it to `conandata.yml` for reproducibility.

## Build Process

1. The project uses a custom Gradle build with Groovy-based `build.gradle`.
2. Since there is no standard Gradle wrapper committed, the build falls back to
   system-installed Gradle.
3. The `distZip` task from the application plugin (applied in the root
   `build.gradle`) packages the application into a distribution zip containing:
   - `bin/` — launcher shell scripts (dex2jar-*)
   - `lib/` — all runtime JARs

## Packaging Strategy

- After `distZip` completes, we locate the generated zip under
  `build/distributions/`, extract it, and copy:
  - The `bin/` directory → package `bin/`
  - The `lib/` directory → package `lib/`
- The entry point scripts (e.g., `d2j-dex2jar`) reference `$APP_HOME/lib/*.jar`
  via `CLASSPATH`, so both directories must be kept at the same relative level.

## Platform Compatibility

- **OS**: Windows, Linux, macOS
- **Architecture**: x86_64, aarch64 (Java is platform-independent)
- Conan settings: `os` and `arch` are used only for package ID; the JARs are
  portable, but the native launcher scripts differ per OS.

## Test Package

A minimal smoke test runs `d2j-dex2jar --help` (or `--version`) to confirm the
binary is executable and the JARs are correctly referenced.

## Known Issues & TODOs

- SHA-256 in `conandata.yml` needs to be filled in after the first successful
  download.
- If the upstream adds a proper Gradle wrapper (gradlew), prefer it over the
  system Gradle.
- The `distZip` task name may differ if the build is restructured; confirm by
  running `gradle tasks` first.
