# Hysteria

Hysteria is a feature-packed proxy & relay tool optimized for lossy, unstable connections
such as satellite networks, public Wi-Fi, and international links from China.

## Features
- Based on QUIC (HTTP/3) protocol
- Custom congestion control algorithms (BBR, Brutal)
- Built-in ACL/routing engine with GeoIP/GeoSite support
- Built-in ACME support for automatic TLS certificates
- Client and server modes

## Build System
- Language: Go
- Build tool: go build (via go.work workspace)
- Entry point: app/main.go
- Build script: hyperbole.py (official)

## Versions
- latest (2.9.3) — published

## Homepage
https://github.com/apernet/hysteria
