# spaln 3.0.7 — OpenHarmony PC (aarch64) adaptation

**spaln** (*space-efficient spliced alignment*) maps and aligns a set of cDNA/EST
or protein sequences onto a whole genomic sequence in a single job.  Upstream is
a C++ program distributed as source only.

| | |
|---|---|
| Upstream | https://github.com/ogotoh/spaln |
| Source tag | `ver.3.0.7` (2025-05-22) |
| License | GPL-2.0-or-later (`LICENSE`, `COPYING`) |
| Build system | hand-written `src/configure` + plain GNU make |
| Conan reference | `spaln/3.0.7` |
| Dependencies | `zlib/1.3.1.1` |

## What the package contains

* `bin/` — 10 of the 14 programs the upstream Makefile can build:
  `spaln`, `sortgrcd`, `makmdm`, `makdbs`, `dvn`, `exinpot`, `kmers`, `npssm`,
  `rdn`, `utn`.
  The four `PROG_F` distribution-fitting tools (`fitild`, `compild`,
  `decompild`, `plotild`) are **not** built — they are the only part of the tree
  that needs glibc-only libc entry points (`exp10`, `drand48_r` /
  `struct drand48_data`) that the OHOS musl libc does not provide.  Upstream's
  own Makefile documents the same reduced set for non-glibc platforms
  (`#PROG = $(PROG_B) $(PROG_A)`) and its `install` target copies `PROG_F` only
  if they exist.  See [notes.md](notes.md).
* `share/spaln/table/` — the 279 parameter tables (baked into the binaries)
* `share/spaln/seqdb/`, `share/spaln/perl/` — sample databases and helper scripts
* `share/man/man1/`, `share/doc/spaln/`, `licenses/`

## Usage

```sh
spaln genomic_segment.fa cdna.fa        # align
spaln -dGenome cdna.fa                  # map and align against a formatted genome
sortgrcd *.grd                          # sort the loci found by spaln
```

The parameter tables are located through the path baked in at configure time
(`<package>/share/spaln/table`).  `$ALN_TAB` overrides it at run time
(`Ftable` searches `.`, then `$ALN_TAB`, then the baked-in path), and the Conan
run environment exports it.

## Adapting notes

See [notes.md](notes.md) for the full adaptation record (build flags, the
`makmdm` / parameter-table decision, verification evidence and known risks).
