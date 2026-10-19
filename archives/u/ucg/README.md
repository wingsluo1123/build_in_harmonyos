# Universal Code Grep

ucg is a concurrent source-code search tool with PCRE2 regular expressions.
It supports file-type selection, recursive search, literal matching, and
case-insensitive matching.

The OHOS arm64 recipe keeps x86 optimizations on x86 and uses the portable
search implementation on ARM. It uses published PCRE2 and argp packages,
GNU Bash/coreutils for the original test shell, Git for benchmark comparisons,
and GoogleTest for the two original unit tests.

The complete upstream suite includes two original expected failures (glob
precedence, groups 28 and 30). These remain visible and are not ordinary passes.
The benchmark comparison diffs are upstream statistics, not assertions of
byte-for-byte equivalence between tools. Full original corpora are required.

Upstream: https://github.com/gvansickle/ucg
