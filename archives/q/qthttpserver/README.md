# qthttpserver

Qt HTTP Server provides C++ APIs for embedding an HTTP server in Qt
applications.

## Available versions

| Version | Status | Build system | Dependency |
|---------|--------|--------------|------------|
| 6.11.1 | built | CMake | qtbase-gui/6.11.1 |

## HarmonyOS PC adaptation

The Conan recipe builds the upstream Qt module against the native CMake
configuration installed by the `qtbase-gui/6.11.1` Conan package. Tests,
examples, benchmarks, and documentation are disabled for the package build;
the separate consumer test constructs `QHttpServer` and checks its initial
listening-port state.

The qtbase-gui package is a mandatory publication prerequisite. The stacked PR
contains that recipe so CI can build it before qthttpserver while the dependency
PR is still under review.
