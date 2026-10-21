# Sofia-SIP

Sofia-SIP is an open-source SIP User-Agent library that implements the IETF RFC 3261 protocol and provides building blocks for voice and real-time communication software.

## Features

- SIP User-Agent core and message handling
- OpenSSL-backed TLS support and zlib support
- Optional GLib event-loop adapter for integrating Sofia timers and I/O with a GLib main loop

## HarmonyOS PC adaptation

The 1.13.18 package targets HarmonyOS PC 6.0 on AArch64 with Clang 15 and libc++. The package is intended to expose both upstream pkg-config modules, sofia-sip-ua and sofia-sip-ua-glib, so downstream consumers can discover the core library and GLib adapter with their transitive dependencies.

## Dependencies

The build uses Conan-managed GLib, OpenSSL, and zlib. The upstream Check framework is used only while building and running the upstream test suite.

## References

- Upstream repository: https://github.com/freeswitch/sofia-sip
- Upstream tag: v1.13.18
- License: LGPL-2.1-or-later
