# rarcrack

rarcrack cracks forgotten passwords of RAR, 7Z and ZIP encrypted archives by
brute force: worker threads probe candidate passwords and verify them with
the external `unrar` / `7z` / `unzip` helpers, resuming from an XML status
file. The `0.2-20240214-413ea3a` recipe builds the upstream single-file
Makefile target with the OHOS toolchain (libxml2 from Conan) and packages
the `rarcrack` executable.
