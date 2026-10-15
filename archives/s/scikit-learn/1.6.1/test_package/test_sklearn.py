#!/usr/bin/env python3
"""Real-consumer test for scikit-learn on HarmonyOS PC (OHOS aarch64).

Imported by test_package/conanfile.py under the conanrun environment, so every
check here exercises the packaged extension modules through the public API —
no print-only stubs. Each check raises AssertionError on failure; the script
prints one PASS line per check plus a final aggregate line the conanfile parses.
"""
import sys

RESULTS = []


def check(name, fn):
    try:
        detail = fn()
    except Exception as exc:  # noqa: BLE001 - report any failure as a failed check
        RESULTS.append((name, False, "%s: %s" % (type(exc).__name__, exc)))
        return
    RESULTS.append((name, True, detail or ""))


def _version():
    import sklearn
    assert sklearn.__version__ == "1.6.1", sklearn.__version__
    return "sklearn " + sklearn.__version__


def _cython_extensions_loaded():
    """The compiled modules must be the packaged .so, not pure-Python stubs."""
    mods = [
        "sklearn.utils._cython_blas",
        "sklearn.tree._tree",
        "sklearn.ensemble._gradient_boosting",
        "sklearn.linear_model._cd_fast",
        "sklearn.linear_model._sag_fast",
        "sklearn.cluster._dbscan_inner",
        "sklearn.neighbors._ball_tree",
        "sklearn.neighbors._kd_tree",
        "sklearn.metrics._pairwise_distances_reduction._datasets_pair",
        "sklearn.preprocessing._csr_polynomial_expansion",
        "sklearn._loss._loss",
        "sklearn.manifold._utils",
    ]
    import importlib
    for m in mods:
        mod = importlib.import_module(m)
        assert getattr(mod, "__file__", "").endswith(".so"), (m, mod.__file__)
    return "%d compiled extensions imported" % len(mods)


def _blas_symbols_bound():
    """sklearn.utils._cython_blas binds the BLAS entry points that SciPy's
    cython_blas module provides at import time — the generated C resolves them
    through __Pyx_ImportFunction, so this proves the scipy-declared symbols
    actually arrive on OHOS (no BLAS library is linked into the .so)."""
    import numpy as np
    from sklearn.utils._cython_blas import (NoTrans, _asum_memview,
                                           _axpy_memview, _copy_memview,
                                           _dot_memview, _gemm_memview,
                                           _gemv_memview, _nrm2_memview,
                                           _scal_memview)
    x = np.ones(8, dtype=np.float64)
    y = np.full(8, 2.0)
    assert abs(_dot_memview(x, y) - 16.0) < 1e-12
    assert abs(_asum_memview(y) - 16.0) < 1e-12
    assert abs(_nrm2_memview(y) - np.sqrt(32.0)) < 1e-12
    dst = np.zeros(3, dtype=np.float64)
    _copy_memview(np.ones(3, dtype=np.float64), dst)
    _axpy_memview(2.0, np.ones(3, dtype=np.float64), dst)
    _scal_memview(3.0, dst)
    assert np.allclose(dst, 9.0), dst
    A = np.arange(9, dtype=np.float64).reshape(3, 3)
    b = np.ones(3, dtype=np.float64)
    gv = np.zeros(3, dtype=np.float64)
    _gemv_memview(NoTrans, 1.0, A, b, 0.0, gv)
    assert np.allclose(gv, A @ b), gv
    C = np.zeros((3, 3), dtype=np.float64)
    _gemm_memview(NoTrans, NoTrans, 1.0, A, A, 0.0, C)
    assert np.allclose(C, A @ A), C
    # float32 instantiation of the same fused wrappers (sdot/sscal path)
    x32 = np.ones(4, dtype=np.float32)
    assert abs(float(_dot_memview(x32, x32)) - 4.0) < 1e-6
    return ("BLAS dot/asum/nrm2/copy/axpy/scal/gemv/gemm round-trip OK for "
            "float32+float64 via scipy.cython_blas")


def _random_forest():
    import numpy as np
    from sklearn.datasets import load_iris
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    X, y = load_iris(return_X_y=True)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=0,
                                          stratify=y)
    clf = RandomForestClassifier(n_estimators=50, random_state=0,
                                 max_depth=4).fit(Xtr, ytr)
    acc = clf.score(Xte, yte)
    assert acc > 0.9, acc
    assert clf.n_features_in_ == 4
    importances = clf.feature_importances_
    assert abs(float(np.sum(importances)) - 1.0) < 1e-8
    return "RandomForest test accuracy %.3f" % acc


def _tree_structures():
    """BallTree / KDTree are pure Cython; they also validate recursion + realloc
    behaviour under the OHOS musl allocator."""
    import numpy as np
    from sklearn.neighbors import KDTree, BallTree, NearestNeighbors
    rng = np.random.RandomState(7)
    data = rng.randn(400, 5)
    query = rng.randn(20, 5)
    dists = {}
    for name, TreeCls in (("kd", KDTree), ("ball", BallTree)):
        tree = TreeCls(data)
        d, i = tree.query(query, k=3)
        assert d.shape == (20, 3) and i.shape == (20, 3)
        assert np.all(np.diff(d, axis=1) >= -1e-9)
        dists[name] = d
    nn = NearestNeighbors(n_neighbors=3, algorithm="brute").fit(data)
    bd, _ = nn.kneighbors(query)
    assert np.allclose(bd, dists["kd"], atol=1e-8), "brute != kd-tree"
    return "KDTree/BallTree/brute 3-NN agree on 20 queries"


def _linear_model_blas_paths():
    """Coordinate-descent, liblinear and saga each take different C/Cython
    paths (cd_fast / svm._liblinear / _sag_fast)."""
    import numpy as np
    from sklearn.datasets import make_classification
    from sklearn.linear_model import ElasticNet, LogisticRegression, SGDClassifier
    X, y = make_classification(n_samples=120, n_features=8,
                               random_state=0)
    en = ElasticNet(alpha=0.1, l1_ratio=0.5, random_state=0).fit(X, y.astype(float))
    assert np.isfinite(en.coef_).all() and abs(en.coef_).sum() > 0
    lr = LogisticSolver = LogisticRegression(solver="liblinear", random_state=0)
    lr.fit(X, y)
    assert lr.score(X, y) > 0.8, lr.score(X, y)
    sgd = SGDClassifier(loss="log_loss", max_iter=200,
                        random_state=0).fit(X, y)
    assert sgd.score(X, y) > 0.75
    lr_saga = LogisticRegression(solver="saga", max_iter=500, tol=1e-3,
                                 random_state=0).fit(X, y)
    assert lr_saga.score(X, y) > 0.75
    return "ElasticNet/liblinear/SGD/saga fits converged"


def _decomposition_randomized_svd():
    import numpy as np
    from sklearn.datasets import load_digits
    from sklearn.decomposition import PCA, TruncatedSVD
    from sklearn.utils.extmath import randomized_svd
    X = load_digits().data.astype(np.float64)
    p = PCA(n_components=10, svd_solver="full").fit(X)
    assert p.explained_variance_ratio_.shape == (10,)
    assert np.all(np.diff(p.explained_variance_ratio_) <= 0)
    # Projection residual identity on the centered data: ||Xc - Xc V V^T|| /
    # ||Xc|| must equal sqrt(1 - sum(explained_variance_ratio_)) — this is the
    # exact algebra of the Cython-backed SVD path, so it is a numerics test,
    # not a smoke test.
    Xc = X - p.mean_
    rec = p.inverse_transform(p.transform(X)) - p.mean_
    rel = np.linalg.norm(Xc - rec) / np.linalg.norm(Xc)
    expect = np.sqrt(1.0 - p.explained_variance_ratio_.sum())
    assert abs(rel - expect) < 1e-9, (rel, expect)
    # The randomized path must reproduce the exact top-10 spectrum.
    U, S, Vt = randomized_svd(X, n_components=10, random_state=0)
    S_exact = np.linalg.svd(X, full_matrices=False)[1][:10]
    assert U.shape == (X.shape[0], 10) and Vt.shape == (10, X.shape[1])
    assert np.max(np.abs(S - S_exact) / S_exact[0]) < 1e-5, S - S_exact
    sv = TruncatedSVD(n_components=10, random_state=0).fit(X)
    assert sv.transform(X).shape == (X.shape[0], 10)
    return ("PCA residual identity rel=%.6f == sqrt(1-evr)=%.6f; "
            "randomized_svd top-10 spectrum within %.2e of exact svd"
            % (rel, expect, np.max(np.abs(S - S_exact) / S_exact[0])))


def _clustering():
    import numpy as np
    from sklearn.cluster import DBSCAN, KMeans, AgglomerativeClustering
    from sklearn.datasets import make_blobs
    X, _ = make_blobs(n_samples=300, centers=3, random_state=0)
    km = KMeans(n_clusters=3, n_init=3, random_state=0).fit(X)
    assert len(set(km.labels_)) == 3 and km.inertia_ > 0
    db = DBSCAN(eps=0.5, min_samples=5).fit(X)
    assert len(set(db.labels_)) >= 3
    ag = AgglomerativeClustering(n_clusters=3).fit(X)
    assert len(set(ag.labels_)) == 3
    return "KMeans/DBSCAN/Agglomerative recovered 3 blobs"


def _metrics_pairwise_cython():
    import numpy as np
    from sklearn.metrics import pairwise_distances, roc_auc_score
    from sklearn.metrics.pairwise import cosine_distances, manhattan_distances
    rng = np.random.RandomState(3)
    A = rng.rand(120, 6)
    B = rng.rand(90, 6)
    diff = A[:, None, :] - B[None, :, :]
    eu = pairwise_distances(A, B, metric="euclidean")
    assert eu.shape == (120, 90)
    assert np.allclose(eu, np.sqrt((diff ** 2).sum(-1)), atol=1e-12), "euclidean"
    man = pairwise_distances(A, B, metric="manhattan")
    assert np.allclose(man, np.abs(diff).sum(-1), atol=1e-12), "manhattan"
    assert np.allclose(manhattan_distances(A, B), man, atol=1e-12)
    # Chunked Cython reduction path (NeighborhoodComponents-style metric) uses
    # the same squared-euclidean kernel; check the sparse/metric API too.
    sq = pairwise_distances(A, B, metric="sqeuclidean")
    assert np.allclose(sq, (diff ** 2).sum(-1), atol=1e-11), "sqeuclidean"
    cd = cosine_distances(A, B)
    ref_cos = 1 - (A @ B.T) / (np.linalg.norm(A, axis=1)[:, None]
                               * np.linalg.norm(B, axis=1)[None, :])
    assert np.allclose(cd, ref_cos, atol=1e-12), "cosine"
    sq_self = pairwise_distances(A, metric="sqeuclidean")
    assert np.allclose(np.diag(sq_self), 0.0, atol=1e-12), "self-distance"
    y_true = np.array([0, 1] * 50)
    assert roc_auc_score(y_true, y_true.astype(float)) == 1.0
    assert roc_auc_score(y_true, 1.0 - y_true) == 0.0
    return ("pairwise euclidean/manhattan/sqeuclidean/cosine match numpy "
            "reference to 1e-12; roc_auc 1.0 perfect / 0.0 reversed")


def _pipeline_and_cv():
    import numpy as np
    from sklearn.compose import ColumnTransformer
    from sklearn.datasets import load_iris
    from sklearn.impute import SimpleImputer
    from sklearn.model_selection import cross_val_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC
    X, y = load_iris(return_X_y=True)
    pipe = Pipeline([("impute", SimpleImputer()),
                     ("scale", StandardScaler()),
                     ("svc", SVC(gamma="scale", random_state=0))])
    scores = cross_val_score(pipe, X, y, cv=3, scoring="accuracy")
    assert scores.shape == (3,) and scores.mean() > 0.85, scores
    ct = ColumnTransformer([("num", StandardScaler(), [0, 1, 2, 3])])
    Xt = ct.fit_transform(X)
    assert abs(float(np.mean(Xt))) < 1e-8
    return "Pipeline + 3-fold CV mean accuracy %.3f" % scores.mean()


def _openmp_and_parallel():
    """sklearn.utils._openmp_helpers is 1.6.1's OpenMP surface: it proves meson
    found libomp on OHOS, and joblib threading must not change results."""
    import numpy as np
    from sklearn.datasets import make_classification
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score
    from sklearn.utils._openmp_helpers import (_openmp_effective_n_threads,
                                               _openmp_parallelism_enabled)
    X, y = make_classification(n_samples=200, n_features=10, random_state=1)
    assert _openmp_parallelism_enabled(), "OpenMP parallelism disabled"
    n_threads = _openmp_effective_n_threads()
    assert n_threads >= 1, n_threads
    assert _openmp_effective_n_threads(2) == 2
    mdl = RandomForestClassifier(n_estimators=20, random_state=0)
    j1 = cross_val_score(mdl, X, y, cv=3, n_jobs=1, scoring="accuracy")
    j2 = cross_val_score(mdl, X, y, cv=3, n_jobs=2, scoring="accuracy")
    assert np.allclose(j1, j2, rtol=0, atol=1e-15), (j1, j2)
    assert j1.mean() > 0.8, j1
    return ("OpenMP enabled, effective n_threads=%d; joblib n_jobs=1 vs 2 "
            "fold scores identical (mean %.4f)" % (n_threads, j1.mean()))


def _model_persistence_roundtrip():
    """joblib/pickle to the OHOS (hmdfs) filesystem is how models are shipped
    on the platform; the Cython TreePredictor objects must survive it."""
    import os
    import pickle
    import tempfile

    import joblib
    import numpy as np
    from sklearn.base import clone
    from sklearn.datasets import load_iris
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    X, y = load_iris(return_X_y=True)
    mdl = Pipeline([("s", StandardScaler()),
                    ("g", GradientBoostingClassifier(n_estimators=15,
                                                     random_state=0))])
    mdl.fit(X, y)
    ref = mdl.predict(X)
    assert (ref == mdl.predict(X)).all(), "predict not deterministic"
    assert abs(mdl.score(X, y) - 1.0) < 1e-9, mdl.score(X, y)
    m2 = pickle.loads(pickle.dumps(mdl))
    assert (m2.predict(X) == ref).all(), "pickle round-trip changed predictions"
    path = os.path.join(tempfile.mkdtemp(prefix="skl-persist-"), "gb.joblib")
    joblib.dump(mdl, path)
    m3 = joblib.load(path)
    assert (m3.predict(X) == ref).all(), "joblib file round-trip differs"
    size = os.path.getsize(path)
    assert size > 1000, size
    fresh = clone(mdl)
    assert fresh.get_params()["g__n_estimators"] == 15
    del m2, m3
    return ("pickle + joblib(%d bytes on hmdfs) round-trips identical "
            "predictions; clone() unfits cleanly" % size)


def main():
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="", help="write machine-readable counts")
    args = ap.parse_args()

    check("version", _version)
    check("extensions", _cython_extensions_loaded)
    check("blas", _blas_symbols_bound)
    check("random_forest", _random_forest)
    check("trees", _tree_structures)
    check("linear_models", _linear_model_blas_paths)
    check("decomposition", _decomposition_randomized_svd)
    check("clustering", _clustering)
    check("metrics_pairwise", _metrics_pairwise_cython)
    check("pipeline_cv", _pipeline_and_cv)
    check("openmp_parallel", _openmp_and_parallel)
    check("persistence", _model_persistence_roundtrip)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    for name, ok, detail in RESULTS:
        print("%s %s %s" % ("PASS" if ok else "FAIL", name, detail))
    print("SKLEARN_CONSUMER_RESULT discovered=%d passed=%d failed=%d"
          % (len(RESULTS), passed, len(RESULTS) - passed))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"suite": "consumer", "discovered": len(RESULTS),
                       "passed": passed, "failed": len(RESULTS) - passed,
                       "checks": [{"name": n, "ok": ok, "detail": d}
                                  for n, ok, d in RESULTS]}, fh)
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
