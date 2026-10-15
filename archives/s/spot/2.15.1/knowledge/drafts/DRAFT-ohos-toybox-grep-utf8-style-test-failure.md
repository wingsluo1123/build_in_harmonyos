# DRAFT-ohos-toybox-grep-utf8-style-test-failure

> Contributor: spot 2.15.1 adaptation (task 10869) | Status: Draft | Updated: 2026-10-04
> Source: archives/s/spot/2.15.1

## Symptom

On the OHOS PC device, the upstream sanity test `tests/sanity/style.test` fails on a
pristine spot 2.15.1 tree with diagnostics on lines that hold a **multibyte UTF-8 glyph**
in a string literal:

```
============================================================
os_ << name << "̅";
.../spot/tl/print.cc: Use << 'c' instead of << "c".
============================================================
print_psl(s << "〈", f) << "〉";
.../spot/twaalgos/compsusp.cc: Use << 'c' instead of << "c".
============================================================
```

The rule is meant for single-byte character literals (`<< "c"` → suggest `<< 'c'`).
The same rule against the same files with GNU grep matches nothing.

## Root Cause

The device default `grep` is **toybox 0.8.12** (`grep --version` prints
`toybox 0.8.12 (is not GNU grep 9.0)`), and it is UTF-8-aware **regardless of
`LC_ALL=C`** - it is one of the implementations the upstream test source explicitly
warns about:

> `# If some grep implementation ignores LC_ALL=C, this rule might be a problem on utf-8 characters such as "δ" ... might be matched as a single character by grep.`

`style.test` exports `LC_ALL=C` and relies on byte semantics for the rule
`'<< *"\([^\\]\|\\.\)"'`: `[^\\]` must consume exactly one **byte**, so a 3-byte glyph
(e.g. `〈` U+2329, `̅` U+0305) can never satisfy `[^\\]\\.\)`-style single-char/escaped-char
matching. Toybox instead matches one **character**, so the rule fires on the glyph and
style.test exits 1 - a toolchain-semantics artifact, not an upstream test defect.

Measured matrix for the verbatim 20-byte rule and sample `x << "〈";` / `y << "c";`:

| grep | locale | multibyte glyph | plain char |
|---|---|---|---|
| toybox 0.8.12 (default PATH) | LC_ALL=C exported | **match (fp)** | match |
| GNU grep 3.12 (hnp) | LANG=en_US.UTF-8 | match (char semantics) | match |
| GNU grep 3.12 (hnp) | LC_ALL=C | **no match** | match |
| busybox 1.37.0 | LANG=en_US.UTF-8 | no match | match |

## Recommended Handling

Do not modify any upstream test file. Arm a GNU grep for the run and let the test's own
`LC_ALL=C` do the rest:

1. `/data/service/hnp/bin/grep` on this device is GNU grep 3.12, but the directory holds
   the whole hnp toolchain - do **not** prepend it (it would shadow `sed`/`awk`/`sh`).
   Copying the binary may also be denied (SELinux hides hnp internals; listing already
   fails with EACCES).
2. Compile a trivial wrapper into a private directory and prepend only that directory:
   ```c
   /* grepwrap.c */
   #include <unistd.h>
   int main(int c, char** v){ v[0]="grep"; execv("/data/service/hnp/bin/grep", v); return 127; }
   ```
   `clang -O2 -o <dir>/grep grepwrap.c && export PATH=<dir>:$PATH`
3. Detect with the same probe the test itself uses - `grep --color=auto -n --version`
   (GNU: rc 0; toybox: rc 2) - so the fix is skipped automatically where a GNU grep
   already resolves first.
4. Verify offline before the full suite: extract the rule verbatim from `style.test`
   (`sed` on the single `$GREP '...'` line or read the file), then
   `LC_ALL=C <gnu-grep> -f rule <multibyte>` → rc 1 and `<plain char>` → rc 0.

Reference: `reports/run-upstream-tests.sh` performs exactly this (arming block before
`make check`, echoing the wrapper path; `SPOT_GNU_GREP` overrides the source path).

## Evidence

spot 2.15.1 on the OHOS PC real device (task 10869):

- Round 5 (`make check` with the device default grep): `style.test` produces the two
  glyph false positives above (the two diagnostic lines are recorded above; that
  round was halted there, all its other tests already green).
- Measurement matrix above (verbatim rule + samples; locale per row as shown).
- Round 6 (same script with the GNU grep arming block): 188/214 pass, 0 fail,
  26 env-guard skips; `style.test` passes with zero glyph false positives - see
  `reports/upstream-test-run.md`; the arming line
  `[run-upstream-tests] 设备默认 grep 非 GNU（UTF-8 误报风险）→ 已封装 .../grep 前置 PATH`
  opens `reports/upstream-test.out`.
- No upstream test file was modified: the fix lives entirely in PATH preparation of the
  reproduction script.

## Reuse Boundary

Applies to any OHOS-class run whose upstream suite contains grep-rule-based style/sanity
checks and resolves `grep` through PATH while the device default is toybox (or any
always-UTF-8 grep). It is the toolchain-semantics sibling of the two exec/loader drafts
for the same suite: `DRAFT-spot-2.15.1-libtool-wrapper-exec-make-check-ohos` (framework
wiring) and `DRAFT-ohos-script-execve-denied-posix-spawn-shim` (runtime script spawning).
Boundaries: it does not help when a test hard-codes an implementation-specific option set
beyond what GNU grep accepts; and where no GNU grep exists at all, fall back to a busybox
copy named `grep` (byte semantics, `\|` works) while stating the substitution.
