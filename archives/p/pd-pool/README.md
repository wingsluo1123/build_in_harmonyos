# pd-pool

`pd-pool/0.2.3` installs the `pool.pd_linux` external and upstream help patch in `lib/pd-externals`.
Load it from Pure Data using `pd -path <package>/lib/pd-externals`.
The package requires `pd-flext/0.6.4`; Conan supplies its runtime library path.

The HarmonyOS native consumer runs six storage and persistence cases against the installed external.
See `0.2.3/notes.md` and `0.2.3/test_package/MANIFEST.yml` for scope and test inventory.
