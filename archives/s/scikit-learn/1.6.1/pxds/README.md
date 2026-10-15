# `pxds/` — build-time-only Cython declarations vendored for OHOS

scikit-learn 1.6.1 needs SciPy's Cython **declarations** to compile 2 sources
directly; 6 further sources pull the same BLAS entry points through sklearn's
own wrapper, so 8 Cython files depend on those declarations in total:

| sklearn source | declaration used |
|---|---|
| `sklearn/utils/_cython_blas.pyx` | `from scipy.linalg.cython_blas cimport sdot/ddot/sgemm/dgemm/…` (11 pairs) — the only direct SciPy BLAS cimport |
| `sklearn/utils/arrayfuncs.pyx`, `sklearn/svm/_liblinear.pyx`, `sklearn/svm/_libsvm.pyx`, `sklearn/svm/_libsvm_sparse.pyx`, `sklearn/cluster/_k_means_lloyd.pyx`, `sklearn/linear_model/_cd_fast.pyx` | `from sklearn.utils._cython_blas cimport …` (transitively the same BLAS entry points) |
| `sklearn/tree/_criterion.pyx` | `from scipy.special.cython_special cimport xlogy` |

Other Cython sources (`tree/_tree.pyx`, `svm/_libsvm_sparse.pyx`,
`ensemble/_gradient_boosting.pyx`, `metrics/cluster/_expected_mutual_info_fast.pyx`,
`cluster/_hdbscan/_reachability.pyx`, `tree/_partitioner.pyx`) only do a
*Python-level* `from scipy… import …`, which needs no declaration file and is
satisfied at import time by the runtime SciPy.

Cython needs only the **`.pxd` declaration files** of SciPy to generate C for
those; the generated code resolves the functions at *import* time through
`__Pyx_ImportFunction`, so no BLAS/special symbol is linked into the `.so`
(`readelf --dynamic` on the built extensions lists only `libpython3.12.so.1.0`,
`libc++_shared.so`, `libc.so`).

SciPy is **not published in the OHPCD Conan registry**
(`https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/`), so a CI
worker building this recipe has no SciPy to point Cython at. SciPy *is*
available for the platform Python as an `ohos_aarch64` wheel from the platform
index `https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple`
(1.14.1 / 1.17.1), which is what satisfies the runtime import.

These two files are therefore vendored verbatim from SciPy **1.14.1**
(`site-packages/scipy/linalg/cython_blas.pxd`,
`site-packages/scipy/special/cython_special.pxd`) so the compile step is
hermetic and offline. They are declarations only — never compiled, never linked,
never installed into the package. `conanfile.py` prefers the real SciPy's own
`.pxd` files whenever the target interpreter can `import scipy`
(`_scipy_declaration_root()`), and falls back to this directory otherwise.

License: SciPy is BSD-3-Clause (Copyright (c) 2001-2002 Enthought, Inc.
2003-2024, SciPy Developers); redistribution of these unmodified declaration
files under that license is what this directory is.
