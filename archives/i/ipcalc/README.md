# ipcalc

## Description
A modern IPv4/IPv6 address calculator tool. Takes an IP address and netmask and calculates the resulting broadcast, network, Cisco wildcard mask, and host range. Supports both IPv4 and IPv6, network deaggregation, and optional GeoIP lookups.

## OHOS Adaptation
- Plain Makefile build, no configure script needed
- No external dependencies required (GeoIP/MaxMind disabled via USE_GEOIP=no USE_MAXMIND=no)
- Compiler path from Conan profile (tools.build:compiler_executables) (R33)
- Makefile has no install target, manual copy in package()
- All 90+ upstream tests pass

## Dependencies
- None (optional: libmaxminddb, geoip — disabled in this build)

## Build
```bash
make USE_GEOIP=no USE_MAXMIND=no
```

## Usage
```bash
ipcalc 192.168.1.1/24
ipcalc 2001:db8::/32
```

## Reference
- Source: https://gitlab.com/ipcalc/ipcalc
- License: GPLv2
