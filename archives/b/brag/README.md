# brag

Download and assemble multipart binaries from newsgroups.

## Overview
brag is a Tcl script tool that grabs and assembles multipart binary attachments from news servers. It uses tclsh as its runtime.

## OHOS Adaptation
- **Shebang fix**: `#!/bin/sh` → `#!/system/bin/sh` (E165)
- **tclsh path**: `exec tclsh` → `exec tclsh8.6` (tcl package provides tclsh8.6)
- **Runtime dependency**: tcl/8.6.16

## Usage
```bash
brag [options] <newsgroup>
```

## Versions
| Version | Status |
|---------|--------|
| 1.4.3   | built  |
