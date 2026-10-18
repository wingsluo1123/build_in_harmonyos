# upstream_pd_tests — upstream unit-test patches, executed verbatim

These three patches are copied **unmodified** from the upstream source tarball
(`unittests/` directory of `vbap-1.2.1.tar.gz`, the archive declared in
`conandata.yml`):

| file | sha256 |
|---|---|
| `vbap-unittest.pd` | `45a4afc8e7f687143b953d4595c2810e24076b1754fe6638bbae9fad4399a7aa` |
| `rvbap-unittest.pd` | `656c07410b1910d8e7bf45569fc83dd2a4d171947899829a8b8fdc0612064490` |
| `define_loudspeakers-unittest.pd` | `e12f328dcba1383819c75dab1373162ca56757188717cced3cb79c36d621c850` |

Upstream repository: <https://github.com/pure-data/vbap> (tag `v1.2.1`).

## Why `testtools/unit-test-frame.pd` lives here

Every upstream patch instantiates `testtools/unit-test-frame` and feeds it the
test name from a `loadbang`. That abstraction is **not** shipped by the upstream
repository, by the Pd distribution, or by this package — without it the patches
stop right after `couldn't create`. `testtools/unit-test-frame.pd` is therefore
supplied by the adapter: it provides the inlet/outlet signature the upstream
patches connect to (4 in / 4 out — the patches connect `frame outlet 3`), echoes
every message it receives as `UNTEST: <name>` and reports on load as
`UNTEST-frame: frame-ready`.

It carries no test logic: all assertions live in `run_upstream_pd_tests.py`, and
the numeric DSP checks of the same three externals are in `consumer_e2e.c`.

## Running

`test_package/conanfile.py` calls `run_upstream_pd_tests.py`, which

1. stages the `vbap/<name>` libdir layout the upstream patches address
   (`vbap/vbap`, `vbap/rvbap`, `vbap/define_loudspeakers`) next to the packaged
   `lib/pd-externals/*.pd_linux`;
2. runs each upstream patch in the packaged Pd host
   (`pd -nogui -nosound -path … -open <patch>`);
3. requires, per patch: it loads, creates every object (no `couldn't create`),
   opens every connection (no `connection failed`), the host reports no `error`,
   and the frame echoes the expected `UNTEST: <name>` marker.
