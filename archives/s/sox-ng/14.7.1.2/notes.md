# sox-ng 14.7.1.2 on HarmonyOS

The package installs the `sox_ng` CLI and the static `libsox_ng` library.
The official Codeberg tag archive is SHA-256 pinned in `conandata.yml`.

## Build choices

- Regenerate Autotools files with Conan `autoconf`, `automake`, and `libtool`
  build requirements because the release archive has `configure.ac` but no
  generated `configure` script.
- Run `autoreconf --force --install` from the source directory in Conan's
  `conanbuild` environment. The declared `autoconf/2.72`, `automake/1.18`, and
  `libtool/2.5.4` tool requirements, with transitive `m4/1.4.19` and
  `perl/5.42.2`, provide the tools and Perl modules from the same Conan graph.
  This keeps `PERL`, `PERL5LIB`, and `M4` consistent and avoids machine-specific
  `$HOME/.harmonybrew` paths on clean CI workers.
- Build verified GNU bc 1.08.2 as a build-only test utility because the device
  has no `bc`; build its library and `bc` executable for the upstream EBU R128
  and chorus/flanger checks (the tests do not use GNU bc documentation outputs).
- Build SoX and its handlers statically; use shared Opus to avoid the CI
  `libopus.a` link-command failure. Conan supplies FLAC, Ogg/Vorbis, Opus,
  WavPack, libsndfile, MP3, AMR, PNG, FFTW, Speex, SpeexDSP, and file-type
  dependencies. SoX's SpeexDSP source also includes `speex/speex_types.h`, so
  both Speex packages are required. Device-only audio backends are disabled.
- Prepend Conan host dependency library directories to `LD_LIBRARY_PATH` for
  build-time probes and upstream tests. The build's source-cache copies of
  `tests.sh` and `testall.sh` preserve those paths when adding their local
  library directory, so optional formats remain enabled during all tests.
- OHOS clang enables upstream OpenMP effects; expose the SDK `libomp` runtime
  as a transitive system library for static consumers. The test package finds
  that compiler runtime from CMake's implicit link directories and adds its
  directory to `LD_LIBRARY_PATH` while running the consumer and CLI, because
  the device loader does not search the SDK directory by default.
- Patch only generated SoX and GNU bc `configure` files in the Conan source
  cache to relax `umask 077`, which creates temporary directories that
  `config.status` cannot write under HMDFS. This changes build-file permissions
  only; the upstream test commands and expected results remain intact.
- Stage upstream vectors and regression directories into the out-of-source
  build tree. The Conan source-cache copy of `test/check.sh` redirects its
  per-case capture from read-only `/tmp` to the writable build tree; the test
  cases themselves are unchanged. Set `SOX_OPTS=--temp <build-dir>` so SoX's
  effect temporary files also use writable storage. The copied `testall.sh`
  writes its two fixed `/tmp/monkey.*` outputs into `build/src` instead.
- Toybox `df` omits HarmonyOS HMDFS mounts despite `statvfs` reporting their
  actual capacity. A build-only `df` adapter reports those values for the
  exact directory used by the upstream 4GB WAV test.

## Upstream test inventory

- `make check`: 71 regression scripts, 99 three-channel format conversions,
  108 sample conversion assertions, and one synth-size assertion.
- `src/tests.sh -1`: 168 mono format conversions, 108 sample conversion
  assertions, and one synth-size assertion.
- `src/tests.sh -2`: 106 stereo format conversions, 108 sample conversion
  assertions, and one synth-size assertion.
- `src/testall.sh`: 23 legacy-format round trips (46 Sox conversions).
- Total upstream census: 794 executions/assertions across all four test
  commands; the Conan consumer package adds eight separate smoke assertions.
- The measured mono/stereo scripts print 168/106 conversion cases (the earlier
  static estimate of 166/105 was low by three); manifests use the observed
  script output, not that estimate.
- The recipe parses each result and fails on a non-OK regression status,
  missing test, skipped format, conversion-count mismatch, or testall error.

The source archive's root `test/run` is a harness template; only the 71
subdirectories containing a `run` file are regression cases. The testall
working-copy filenames keep a dot before each original format suffix so SoX
selects the same handlers as the upstream `/tmp/monkey.$format` paths.
