# libbson

libbson is a BSON serialization library, part of the mongo-c-driver project.
It provides utilities for creating, parsing, and manipulating BSON documents.

## Available Versions

- **2.5.6** (built): Built from the mongo-c-driver GitHub archive (tag 2.5.6) with cmake `-DENABLE_MONGOC=OFF`; 2.x package line: `libbson2.so.2`, headers at `include/bson-2.5.6/bson/`, pkg-config `bson2.pc`
- **1.27.1** (published): Built from Savannah release tarball with cmake; 1.x package line: `libbson-1.0.so.0`, headers at `include/libbson-1.0/`

## Build Notes

- Build system: cmake
- 2.x line: `ENABLE_MONGOC=OFF` is the upstream-sanctioned switch that limits the monorepo build to the bundled libbson; zero external dependencies
- 1.x line: Savannah release tarballs include generated cmake modules (build/cmake/); GitHub archive tarballs lack these modules
- The two package lines install disjoint artifact names and can coexist in one prefix

## Quality Status

### 2.5.6
- Local `conan create` (ohos-aarch64 profile): PASS
- Upstream tests really executed in build() (2026-10-11 rule4 fix): 529 entries via unpatched upstream test-libmongoc vehicle — 526 pass / 3 skip (documented) / 0 fail, case-level 1476/1479
- Consumer test (test_package/test_bson.c): 104/104 pass — see notes.md

### 1.27.1
- Quality gates G1-G4: PASS
- Functional test: 52/52 pass (2026-06-01)
- Pre-compiled package: ready for upload
