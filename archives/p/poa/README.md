# POA — Partial Order Alignment

Upstream: https://sourceforge.net/projects/poamsa/

POA builds partial-order multiple sequence alignments and heaviest-bundle consensus.
The package provides liblpo.a, poa, eight headers, score matrices and example data.
Dependencies: system C runtime and libm.

```sh
poa -read_fasta INPUT.fa -clustal OUTPUT.aln PACKAGE/share/poa/blosum80.mat
```

CMake: `find_package(poa CONFIG REQUIRED)` and `poa::lpo`.
The target propagates the required USE_WEIGHTED_LINKS/USE_PROJECT_HEADER definitions.
The optional BLAST helper make_pscores.pl is included; its external toolchain is untested.
