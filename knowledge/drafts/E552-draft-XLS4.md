# Filename envelopes and exact structured CLI data

When the same input is copied into a Chinese path containing spaces, different
stdout does not by itself establish a data-conversion bug. Some C/C++ tools
deliberately include `FILE: <input>` before the data. Help text may also describe
a separator different from the one selected by the actual implementation.

First prove the output grammar from the upstream source. Verify the exact
filename-bearing envelope independently, including the non-ASCII bytes. Split
only at that proven boundary; compare the remaining payload byte-for-byte and
parse using the actual separator. Keep an independent structural oracle and an
invalid-input failure check. Do not remove arbitrary lines or weaken equality
to substring/nonempty checks.

The native libxls 1.6.4 experiment is a concrete counterexample: the input path
is printed on stdout and the actual default separator is `;`, while usage says
comma. Its first worksheet was independently checked through the C API as 24
rows and 11 columns. The final installed CLI test validates three sheet names,
each exact filename banner, identical conversion payload, 24x11 parsed geometry
and missing-input failure. Shared and static Conan builds both passed upstream
3/3 and packaged consumers 2/2; log SHA-256 is
`98c1c44e0aaa297b8dec4f8425538a0e167a403f1d88514bc4d215dfca103e9b`.

This extends generic functional-testing guidance with an exact variable-envelope
boundary and a source/help mismatch counterexample; it is not a replacement for
data checks. Apply only when the protocol is proven. Binary stdout, arbitrary
diagnostics or unproven boundaries must remain fail-closed. No upstream code,
test case or platform security setting was removed to obtain the passing result.
