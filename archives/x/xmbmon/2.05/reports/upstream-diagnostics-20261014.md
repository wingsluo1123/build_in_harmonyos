# Upstream hardware diagnostics, 2026-10-14

Source: unmodified `xmbmon205.tar.gz`, SHA-256
`65b10ebfe53585ac22d6a31d8ef3fea552cb266cf2c124c00421dec1df5a4a4f`.
Environment: WSL Ubuntu x86_64, UID 1000. The old `config.sub` needs
the explicit i686 aliases below; the actual compiler targets x86_64.

```sh
./configure --without-x --build=i686-pc-linux-gnu --host=i686-pc-linux-gnu
make -j1 smbuses.o smbus_piix4.o smbus_amd.o smbus_ali.o smbus_amd8.o
make -j1 testprog
```

Each command below used `timeout 10s ./NAME`, capturing combined stdout/stderr
and the program exit status. The complete raw transcript was captured at
`output/xmbmon-2.05/publish/upstream-diagnostics-20261014.log`, SHA-256
`10aa2fc85b6440444d0c7aae0670401430481bc2039a0748895fec29c5c60435`.
The per-command output is reproduced here without changing the results.

```text
$ ./testpci
exit=255
Cannot open IO-port, needs privilege!
Listing Bus:0 PCI Configuration: ChipID

$ ./testsmb
exit=255
Cannot open IO-port, needs privilege!

$ ./testhwm
exit=255
No SMBus candidates found!!

$ ./testfan
exit=255
No SMBus candidates found!!
```

Follow-up in the same WSL instance with `wsl --user root` also failed:

```text
$ ./testpci
Listing Bus:0 PCI Configuration: ChipID
Cannot open IO-port, needs privilege!

$ ./testhwm
No SMBus candidates found!!
```

The root check confirms the same errors, not a distinct root exit code:
the `wsl.exe` wrapper returned nonzero but the shell's raw program status
was not separately captured. `testhwm.c` groups a `-1` I/O-open failure
with a true zero-candidate result in the same message. Neither message
establishes whether this machine has a compatible SMBus controller.
