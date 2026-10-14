# KDSoap WS-Discovery Client

KDSoap WS-Discovery Client is a Qt library that implements the client side of the WS-Discovery protocol for discovering SOAP services on local networks.

## Features

- Sends WS-Discovery Probe and Resolve messages.
- Parses ProbeMatches and ResolveMatches into `WSDiscoveryTargetService` objects.
- Provides the exported CMake target `KDSoap::WSDiscoveryClient`.

## HarmonyOS adaptation

- Built natively for HarmonyOS PC aarch64 with Qt 6 and KDSoap.
- The Conan recipe sets CMake's platform name to Linux for its platform-module logic; the compiler and Conan host profile still target OHOS aarch64.
- The Conan test package includes a real loopback UDP exchange and SOAP ProbeMatches parsing test on HarmonyOS.
- WS-Discovery network discovery depends on the device network allowing UDP multicast; the loopback integration test does not require an external discovery device.

## Dependencies

- Build and runtime: `qtbase/6.11.1`, `kdsoap/2.3.0`.
- Build only: `extra-cmake-modules/6.29.0`.

## References

- Project: https://invent.kde.org/libraries/kdsoap-ws-discovery-client
- Release archive: https://download.kde.org/Attic/kdsoap-ws-discovery-client/kdsoap-ws-discovery-client-0.4.0.tar.xz
