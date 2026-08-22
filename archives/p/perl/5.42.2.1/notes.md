# perl 5.42.2.1 adaptation notes

## Version model

- Conan package version: `perl/5.42.2.1`
- Upstream source and runtime version: Perl `5.42.2`
- Source archive: `perl-5.42.2.tar.gz`
- Source SHA256: `9384e8deb75b7b1695e5637971b752281aaecd025a3d5d4734d33c1d0adfee47`

The fourth component is an OpenHarmony package revision. It does not claim an upstream Perl 5.42.2.1 release. The software-level `commands.json` retains both mappings: `5.42.2` points to the published legacy package and `5.42.2.1` points to this compatibility revision.

## Compatibility fix

CI build #33233 completed PR checkout but failed while GNU Parallel loaded Perl's native `Fcntl` module:

```text
Can't load .../auto/Fcntl/Fcntl.so: Error loading shared library ... Permission denied
```

OHOS requires executable ELF files and dynamically loaded XS modules to carry a valid `.codesign` section before they enter the Conan package cache. This recipe therefore:

1. signs `perl`, `perl5.42.2`, and all built XS `.so` files in the build tree;
2. installs the signed artifacts into the Conan package;
3. verifies every delivered Perl executable and XS `.so` has a `.codesign` section;
4. fails packaging when signing tools are absent, no ELF was signed, or package verification fails.

The existing OHOS adaptations remain unchanged: build-local temporary directories, copy-based link emulation, writeability probes, disabled `prctl` process-name handling, and exclusion of unsupported SysV IPC.

## Verification

The following command passed with the repository OHOS aarch64 profile:

```sh
conan create . \
  --profile:host=ci/conan/profiles/ohos-aarch64 \
  --profile:build=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

Observed consumer-test output:

```text
perl 5.042002 ok
os=linux; arch=aarch64-linux-thread-multi; sep=a/b
XS modules ok
script ok
```

The test executes the packaged interpreter, loads pure-Perl core modules, loads native `Fcntl` and `POSIX` XS modules, and runs a strict/warnings script. It is not an output-only smoke test.
