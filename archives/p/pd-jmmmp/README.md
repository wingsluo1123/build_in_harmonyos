# pd-jmmmp

`pd-jmmmp/0.61` packages Joao Pais' **jmmmp** library for Pure Data: 72 GUI and
utility abstractions for musical performance (Granulator, multiarray, jp.coll,
jp.menu, mat~/maat~ level meters, clock/uhr/stoppuhr, bezier~ transfer
functions, ...), their 68 `-help.pd` patches, the `jmmmp-meta.pd` libdir
marker, twelve `.txt` data files and 38 example images.

The release is pure Pd data - upstream ships no Makefile and no source code -
so the recipe compiles nothing and installs the upstream file set to
`lib/pd-externals/jmmmp/`, the same layout Debian uses
(`/usr/lib/pd/extra/jmmmp/`).

## Using it from Pure Data

```sh
pd -path <package>/lib/pd-externals/jmmmp \
   -path <package>/lib/pd-externals    # only needed for the jmmmp/<name> form
```

or, from a patch, `[declare -path <package>/lib/pd-externals/jmmmp]`. The
first entry makes the flat names (`[scale]`) resolvable; the second makes the
namespaced names that some upstream patches use (`[jmmmp/scale]`,
`[jmmmp/dsp01]`, `[jmmmp/lbang]`, `[jmmmp/metrum]`) resolvable.

## Runtime prerequisites

49 of the 72 abstractions need nothing but Pd itself. The other 23 reference
classes from other Pd libraries; the libraries named by their own `[declare]`
lines are zexy (11 abstractions declare it), cyclone, ggee, iemlib, iem_tab,
iemmatrix, list-abs, maxlib, mrpeach, Gem, ceammc and pd-ableton-link, plus
`oscx` (used by `oscD`/`oscS` without a declare) and `abl_link~`
(`live2reaper`). Four of the 23 declare nothing at all
(`ml.poly.granulator`, `oscD`, `oscS`, `stoppuhr-clock`), so the declarations
are not a complete statement of what a given patch needs.

These are runtime prerequisites of the Pd installation, not Conan
dependencies; Debian expresses the same set as `Recommends` (`gem`,
`pd-ableton-link`, `pd-cyclone`, `pd-ext13`, `pd-ggee`, `pd-iemlib`,
`pd-iemmatrix`, `pd-iemutils`, `pd-list-abs`, `pd-maxlib`, `pd-mrpeach`,
`pd-zexy`). The complete per-abstraction class map is in `0.61/notes.md`.

## Consumer test

The consumer test is the whole quality gate (upstream has no test suite). It
checks the packaged inventory and the structural validity of all 141 patches,
builds the complete class dependency map, and then runs the 49 vanilla-only
abstractions plus nine deterministic behaviour assertions in a headless Pd
from `puredata/0.56.5`, with a negative control that removes the package from
Pd's search path. Host run: 173 assertions, 0 failed.

See `0.61/notes.md` for scope, the full evidence and the next steps. The
consumer test passes on the host and on the HarmonyOS PC (isolated shadow CI,
`Total: 1 / Success: 1`, L0/L1/L4/L5 pass); the package is marked `built` in the
manifest and has not been uploaded yet.
