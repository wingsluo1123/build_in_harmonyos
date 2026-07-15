# wireless-regdb

Linux Wireless Regulatory Database — provides regulatory rules for wireless communication (WiFi, Bluetooth, etc.).

## Overview

wireless-regdb is the regulatory database used by the Linux wireless subsystem. It contains:
- `regulatory.bin` — binary regulatory database (CRDA format)
- `regulatory.db` — binary regulatory database (firmware format, kernel ≥ 4.15)
- `regulatory.db.p7s` — cryptographic signature for regulatory.db
- Public keys for signature verification

## Build

```bash
make -j1
make install DESTDIR=<prefix> PREFIX=/usr
```

No `configure` step needed. The Makefile generates database files from `db.txt` using Python scripts (`db2bin.py`, `db2fw.py`) and signs them with openssl.

## OHOS Adaptation

- Patch shebangs: `python` → `python3`, `/bin/bash` → `/usr/bin/env bash`
- No C/C++ compilation required (pure data package)
