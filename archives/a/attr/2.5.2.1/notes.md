# attr 2.5.2.1 device build notes

- Source: upstream attr 2.5.2 static release tarball from the CI mirror-covered Savannah download host; SHA-256 `39bf67452fa41d0948c2197601053f48b3d78a029389734332a6309a680c6c87`.
- License review: upstream documentation and source headers identify libattr as LGPL-2.1-or-later and the getfattr, setfattr, and attr tools as GPL-2.0-or-later.
- Adaptation path: A. No knowledge-base proposal or Issue was needed.
- `0001`/`0002` add OHOS target-triplet recognition. The first device configure attempt failed at `./config.status: line 822: ./confOOcNPA/subs1.awk: Permission denied`; the raw failure traced to HMDFS UID mapping with upstream `umask 077`. `0003` changes only the two configure temp-directory umasks to `022`; the subsequent create completed.
- The first test-run attempt with the Conan Perl package failed before command cases because its `Cwd.so` could not resolve `Perl_newSVsv_flags`. The recipe now uses Perl from the active build PATH. Core modules loaded on device.
- Device command: `conan create ... -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`, `-j2`, `CONAN_HOME=~/work/psj/ch-attr`; `CREATE_EXIT=0`.
- Upstream suite: `make check VERBOSE=1 TEST_LOG_COMPILER='perl -U -w $(srcdir)/test/run -v'`; registered N=149 (119 + 30), 87 pass, 32 fail, 30 not run; `make check` exit 2. Every failing and unrun source command, raw output evidence, and concrete cause are listed in `test_package/MANIFEST.yml`. The suite's Perl runner compares stdout/stderr, does not preserve child exit status, and did not emit raw errno for the output mismatches. The device consumer test independently succeeded on xattrs, so no errno is claimed for those rows.
- The root-only group ended before its first command with `FAIL test/root/getfattr.test (exit status: 159)`. `sudo -n true` returned `open /dev/tty for write failed` (exit 1), so effective UID 0 was unavailable to this SSH session; all 30 root-group commands are marked not run.
- The test package passed 6/6: `attr_set`/`attr_get` on a build-folder temp file, plus setfattr/getfattr/attr set/get resolved from the tested package's `bin/` directory. No filesystem xattr errno was generated.
- `test_package/MANIFEST.yml` is the per-case evidence source. No upstream tests were modified.
