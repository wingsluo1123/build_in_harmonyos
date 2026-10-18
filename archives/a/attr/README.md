# attr

The `attr` package provides the upstream extended-attribute tools and the
`libattr` compatibility API.

## Components and licenses

| Component | SPDX license |
|---|---|
| `libattr` | LGPL-2.1-or-later |
| `getfattr`, `setfattr`, `attr` | GPL-2.0-or-later |

The expressions follow upstream `doc/COPYING`, `doc/COPYING.LGPL`, and the
corresponding source headers.

## Versions

| Conan version | Source | Status |
|---|---|---|
| 2.5.2 | attr 2.5.2 | Recipe merged in !1539; its only CI run failed at `checkout-pr`, and no `attr` package is in the registry. |
| 2.5.2.1 | attr 2.5.2 | Device create succeeded; PR publication is pending. |

## OHOS adaptation

- Adds the HarmonyOS `linux-ohos` target to upstream `config.guess` and
  `config.sub`.
- Builds static `libattr.a` and the `getfattr`, `setfattr`, and `attr` tools.
- Uses `umask 022` for `configure` temporary directories. The device initially
  failed with `./config.status: line 822: ./confOOcNPA/subs1.awk: Permission denied`
  because HMDFS UID mapping rejected writes through the upstream `umask 077`
  directory.
- Exports Conan component `libattr` with `attr/attributes.h`, `attr/libattr.h`,
  and `attr/error_context.h` and CMake target `attr::libattr`.

## Validation

The upstream suite registers 149 command checks: 119 in `test/attr.test` and 30
in `test/root/getfattr.test`. On the HarmonyOS device, 87 passed, 32 failed on
observed output mismatches, and 30 root-only checks were not run because the
SSH device user could not obtain effective UID 0. The upstream Perl runner does
not retain child exit statuses, so the mismatch rows contain the raw output it
recorded and do not claim an errno that it did not emit. All 6 test-package
checks passed, including `attr_set`/`attr_get` and the package's three CLI tools.
Per-case results and raw evidence are in `2.5.2.1/test_package/MANIFEST.yml`.

## Upstream source

- Project: <https://savannah.nongnu.org/projects/attr>
- Static release archive: <https://download.savannah.gnu.org/releases/attr/attr-2.5.2.tar.gz>
- SHA-256: `39bf67452fa41d0948c2197601053f48b3d78a029389734332a6309a680c6c87`
