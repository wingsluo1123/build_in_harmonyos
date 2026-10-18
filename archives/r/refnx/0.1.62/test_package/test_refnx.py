#!/usr/bin/env python3
"""Real-consumer test for refnx on HarmonyOS PC (OHOS aarch64).

Run by test_package/conanfile.py under the conanrun environment, so every check
exercises the extension modules built by this recipe through the public API —
no print-only stubs. The live channel needs the platform's OHOS wheels for scipy
(and pandas/orsopy for the loader checks), which are runtime dependencies of the
platform Python rather than Conan requirements; test_package/conanfile.py falls
back to static artifact verification when they are absent.

The reference values come from three independent implementations, which is what
makes these checks meaningful rather than self-fulfilling:

  * `_creflect.abeles`     C, compiled from src/refcalc.c
  * `_cyreflect.abeles`    Cython + OpenMP (`prange` over the Q points)
  * `_reflect.abeles`      the pure-Python translation shipped upstream
  * `theoretical.txt`      reflectivity computed by Motofit, shipped in the sdist

Agreement between the two Cython kernels and the pure-Python one proves the OHOS
build did not break the numerical core; agreement with Motofit's numbers proves
the physical model itself is right.
"""
import os
import pickle
import sys

RESULTS = []


def check(name, fn):
    try:
        detail = fn()
    except Exception as exc:  # noqa: BLE001 - report any failure as a failed check
        RESULTS.append((name, False, "%s: %s" % (type(exc).__name__, exc)))
        return
    RESULTS.append((name, True, detail or ""))


def _paths():
    import refnx
    root = os.path.dirname(refnx.__file__)
    return refnx, os.path.join(root, "reflect", "tests"), \
        os.path.join(root, "dataset", "tests")


def _version():
    import refnx
    assert refnx.__version__ == "0.1.62", refnx.__version__
    return "refnx " + refnx.__version__


def _compiled_extensions_loaded():
    """The compiled modules must be the packaged .so, not pure-Python fallbacks."""
    import importlib
    mods = ["refnx._lib._cutil", "refnx.reflect._creflect",
            "refnx.reflect._cyreflect", "refnx.reduce._cevent"]
    for m in mods:
        mod = importlib.import_module(m)
        assert getattr(mod, "__file__", "").endswith(".so"), (m, mod.__file__)
    return "%d compiled extensions imported" % len(mods)


def _cutil_vs_python_reference():
    """`_cutil` is the C flatten/unique that refnx falls back to for ragged
    sequences; the pure-Python equivalents ship in refnx._lib."""
    import numpy as np
    from refnx._lib import _cutil, flatten, unique
    ragged = [[0.0, 1.0], np.arange(5.0), [], (2.5,), [7.0] * 3]
    assert list(_cutil.c_flatten(ragged)) == list(flatten(ragged))
    dupes = [3, 1, 3, 2, 1, 7, 7, 2, 9]
    assert list(_cutil.c_unique(dupes)) == list(unique(dupes))
    return "c_flatten/c_unique agree with the pure-Python reference"


def _structure_and_reference():
    """The structural model and the Motofit reference reflectivity, shared by
    several checks below."""
    import numpy as np
    from refnx.reflect import SLD
    _, rtests, _ = _paths()
    sio2, air, si = SLD(3.47, name="SiO2"), SLD(0, name="air"), SLD(2.07, name="Si")
    structure = air | sio2(100, 2) | si(0, 3)
    theoretical = np.loadtxt(os.path.join(rtests, "theoretical.txt"))
    qvals, rvals = np.hsplit(theoretical, 2)
    return structure, qvals.flatten(), rvals.flatten()


def _abeles_matches_motofit_reference():
    from refnx.reflect import _creflect
    structure, q, r = _structure_and_reference()
    calc = _creflect.abeles(q, structure.slabs()[..., :4])
    rel = float((abs(calc - r) / r).max())
    assert rel < 1e-9, rel
    return ("_creflect.abeles reproduces the sdist's Motofit reference on %d "
            "Q points (max rel dev %.2e)" % (q.size, rel))


def _all_backends_agree():
    """The backend-selection layer (_reflect / _creflect / _cyreflect, Abeles and
    Parratt) must all land on the same curve; the OHOS build enables OpenMP and
    the C++ translation units, so this is where a broken kernel shows up."""
    from refnx.reflect import reflect_model as rm
    structure, q, r = _structure_and_reference()
    slabs = structure.slabs()[..., :4]
    worst = {}
    for backend in sorted(rm.available_backends()):
        with rm.use_reflect_backend(backend) as kernel:
            calc = kernel(q, slabs)
        worst[backend] = float((abs(calc - r) / r).max())
    bad = {b: v for b, v in worst.items() if not v < 1e-9}
    assert not bad, bad
    return ("%d backends (%s) match the Motofit reference to < 1e-9"
            % (len(worst), ", ".join(sorted(worst))))


def _abeles_c_vs_pure_python():
    from refnx.reflect import _creflect, _reflect
    structure, q, _ = _structure_and_reference()
    slabs = structure.slabs()[..., :4]
    dev = float(abs(_creflect.abeles(q, slabs) - _reflect.abeles(q, slabs)).max())
    assert dev < 1e-12, dev
    return "C refcalc.c and the pure-Python Abeles kernel agree to %.1e" % dev


def _parratt_matches_abeles():
    from refnx.reflect import _creflect
    structure, q, r = _structure_and_reference()
    slabs = structure.slabs()[..., :4]
    par = _creflect.parratt(q, slabs)
    dev = float((abs(par - r) / r).max())
    assert dev < 1e-9, dev
    return "Parratt recursion matches Abeles/Motofit to %.2e" % dev


def _abeles_vectorised_equals_scalar():
    """abeles_vectorised batches many parameter sets through one C call (the
    path a fitter uses); each stack must equal a scalar abeles evaluation."""
    import numpy as np
    from refnx.reflect import _creflect, abeles
    structure, _, _ = _structure_and_reference()
    coefs = structure.slabs()[..., :4]
    stack = np.repeat(coefs[None, :, :], 5, axis=0)
    for k in range(5):
        stack[k, :, 1] = coefs[:, 1] + 0.2 * k
    q = np.geomspace(0.005, 0.5, 251)
    got = np.asarray(_creflect.abeles_vectorised(q, stack))
    want = np.array([abeles(q, stack[k]) for k in range(5)])
    assert got.shape == want.shape, (got.shape, want.shape)
    dev = float(abs(got - want).max())
    assert dev < 1e-15, dev
    return ("abeles_vectorised over %d stacks equals the scalar kernel "
            "(max dev %.1e)" % (stack.shape[0], dev))


def _gepore_nonmagnetic_channels_equals_abeles():
    """gepore is the polarised-neutron kernel (C++ + the pnr sources). With zero
    magnetic SLD the non-spin-flip channels must collapse onto the unpolarised
    Abeles result, and the spin-flip channels onto zero."""
    import numpy as np
    from refnx.reflect import _creflect
    from refnx.reflect._creflect import gepore
    structure, _, _ = _structure_and_reference()
    coefs = structure.slabs()[..., :4]
    w = np.zeros((coefs.shape[0], 6))
    w[:, :4] = coefs
    q = np.geomspace(0.005, 0.5, 201)
    out = np.asarray(gepore(q, w, H=0.0, Aguide=270))
    assert out.shape == (4, q.size), out.shape
    unpolarised = _creflect.abeles(q, coefs)
    dev = max(float(abs(out[0] - unpolarised).max()),
              float(abs(out[3] - unpolarised).max()))
    assert dev < 1e-12, dev
    mine = float(max(abs(out[1]).max(), abs(out[2]).max()))
    assert mine < 1e-20, mine
    return ("gepore non-spin-flip channels equal the unpolarised kernel "
            "(max dev %.1e), spin-flip channels stay at zero (%.1e)"
            % (dev, mine))


def _cyreflect_openmp_thread_invariance():
    """_cyreflect parallelises the Q loop with OpenMP. On the OHOS build libomp
    is linked, so the same input through 0 (all cores), 1 and 4 threads must be
    bit-identical — and identical to the single-threaded C kernel."""
    import numpy as np
    from refnx.reflect import _creflect, _cyreflect
    structure, q, _ = _structure_and_reference()
    slabs = structure.slabs()[..., :4]
    c = _creflect.abeles(q, slabs)
    r1 = _cyreflect.abeles(q, slabs, threads=1)
    r4 = _cyreflect.abeles(q, slabs, threads=4)
    r0 = _cyreflect.abeles(q, slabs, threads=0)
    assert np.array_equal(r1, r4), float(abs(r1 - r4).max())
    assert np.array_equal(r1, r0), float(abs(r1 - r0).max())
    dev = float(abs(r1 - c).max())
    assert dev < 1e-12, dev
    return ("_cyreflect/OpenMP bit-identical for threads=0/1/4 and equal to the "
            "C kernel (max dev %.1e)" % dev)


def _structure_reflectivity_uses_packaged_kernel():
    """Structure.reflectivity() is the user-facing entry point: it microslabs the
    component tree and dispatches to the compiled kernel."""
    from refnx.reflect import _creflect
    structure, q, r = _structure_and_reference()
    got = structure.reflectivity(q)
    kernel = _creflect.abeles(q, structure.slabs()[..., :4])
    dev = float(abs(got - kernel).max())
    assert dev < 1e-15, dev
    assert float((abs(got - r) / r).max()) < 1e-9
    return ("Structure.reflectivity() == packaged kernel (max dev %.1e) and "
            "matches the Motofit reference" % dev)


def _spline_profile():
    """Spline microslabs a continuous profile into a graded stack; a uniform
    spline must therefore reproduce a plain uniform slab."""
    import numpy as np
    from refnx.reflect import SLD, Spline
    air, si = SLD(0, name="air"), SLD(2.07, name="Si")
    q = np.linspace(0.008, 0.3, 200)
    spline = Spline(100, [2.07] * 20, [0.05] * 20, microslab_max_thickness=1)
    graded = (air | spline | si(0, 3)).reflectivity(q)
    plain = (air | si(100, 0) | si(0, 3)).reflectivity(q)
    dev = float(abs(graded - plain).max())
    assert dev < 1e-3, dev
    assert ((graded >= 0) & (graded <= 1 + 1e-6)).all(), (graded.min(),
                                                          graded.max())
    return ("uniform Spline reproduces the equivalent slab stack (max abs dev "
            "%.1e on R)" % dev)


def _objective_chisqr_and_nll():
    """Objective is what every fitter maximises; verify the likelihood
    bookkeeping on a synthetic dataset whose optimum is known analytically."""
    import numpy as np
    from refnx.analysis import Objective
    from refnx.dataset import ReflectDataset
    from refnx.reflect import ReflectModel, SLD
    air, sio2, si = (SLD(0, name="air"), SLD(3.47, name="SiO2"),
                     SLD(2.07, name="Si"))
    q = np.linspace(0.008, 0.3, 150)
    rng = np.random.default_rng(0)
    model = ReflectModel(air | sio2(100, 2) | si(0, 3), dq=0.0)
    truth = model(q)
    dataset = ReflectDataset((q, truth * (1 + rng.normal(0, 0.01, q.size)),
                              truth * 0.01))
    objective = Objective(model, dataset)
    flat = {p.name: p for p in objective.parameters.flattened()}
    thick = flat["SiO2 - thick"]
    assert objective.npoints == q.size, objective.npoints
    dev = abs(objective.chisqr() / objective.npoints - 1.0)
    assert dev < 0.5, objective.chisqr() / objective.npoints
    assert abs(objective.nll() + objective.logl()) < 1e-9
    thick.vary = True
    thick.setp(value=70)
    worse = objective.chisqr()
    thick.setp(value=100)
    assert objective.chisqr() < worse
    return ("chi2/npoint=%.3f at the true parameter set, nll == -logl, and the "
            "parameters tree exposes %d parameters"
            % (objective.chisqr() / objective.npoints, len(flat)))


def _curvefitter_recovers_thickness():
    """End-to-end scipy-backed fit: start 5 A away from the answer and let
    L-BFGS-B find the layer thickness of the synthetic dataset."""
    import numpy as np
    from refnx.analysis import CurveFitter, Objective
    from refnx.dataset import ReflectDataset
    from refnx.reflect import ReflectModel, SLD
    air, sio2, si = (SLD(0, name="air"), SLD(3.47, name="SiO2"),
                     SLD(2.07, name="Si"))
    q = np.linspace(0.008, 0.3, 150)
    rng = np.random.default_rng(0)
    model = ReflectModel(air | sio2(100, 2) | si(0, 3), dq=0.0)
    truth = model(q)
    dataset = ReflectDataset((q, truth * (1 + rng.normal(0, 0.01, q.size)),
                              truth * 0.01))
    objective = Objective(model, dataset)
    flat = {p.name: p for p in objective.parameters.flattened()}
    thick = flat["SiO2 - thick"]
    thick.vary = True
    thick.setp(value=95)
    thick.setp(bounds=(50, 150))
    fitter = CurveFitter(objective)
    fitter.fit(verbose=False)
    got = float(thick.value)
    assert abs(got - 100) < 0.5, got
    assert objective.chisqr() < 300, objective.chisqr()
    assert 0 < float(thick.stderr) < 5, thick.stderr
    return ("CurveFitter.fit recovered %.3f A (truth 100, stderr %.3f), "
            "chi2=%.1f" % (got, float(thick.stderr), objective.chisqr()))


def _mcmc_posterior():
    """CurveFitter.sample drives the vendored emcee (with the emcee3-style
    sampler shim) through the same objective — the OHOS numpy/scipy stack has to
    support the whole MCMC path, not just the minimiser."""
    import numpy as np
    from refnx.analysis import CurveFitter, Objective
    from refnx.dataset import ReflectDataset
    from refnx.reflect import ReflectModel, SLD
    air, sio2, si = (SLD(0, name="air"), SLD(3.47, name="SiO2"),
                     SLD(2.07, name="Si"))
    q = np.linspace(0.008, 0.3, 100)
    rng = np.random.default_rng(0)
    model = ReflectModel(air | sio2(100, 2) | si(0, 3), dq=0.0)
    truth = model(q)
    dataset = ReflectDataset((q, truth * (1 + rng.normal(0, 0.01, q.size)),
                              truth * 0.01))
    objective = Objective(model, dataset)
    flat = {p.name: p for p in objective.parameters.flattened()}
    thick = flat["SiO2 - thick"]
    thick.vary = True
    thick.setp(value=95)
    thick.setp(bounds=(50, 150))
    fitter = CurveFitter(objective)
    fitter.fit(verbose=False)
    fitter.sample(120, random_state=1, verbose=False)
    chain = objective.parameters.varying_parameters()[0].chain
    assert chain.ndim == 2 and chain.size > 1000, chain.shape
    mean = float(chain.mean())
    assert abs(mean - 100) < 0.5, mean
    return ("emcee posterior on %s walkers x %d steps: thickness %.3f +/- %.3f"
            % (chain.shape[1], chain.shape[0], mean, float(chain.std())))


def _dataset_loaders():
    """Data1D (dot format), ReflectDataset (e361r) and the ORSO/orsopy round-trip
    all touch pandas + orsopy, i.e. the platform wheels rather than the C core."""
    import numpy as np
    from refnx.dataset import Data1D, OrsoDataset, ReflectDataset
    refnx, _, dtests = _paths()
    assert refnx.__version__ == "0.1.62"
    d1 = Data1D(os.path.join(dtests, "dot.out"))
    assert d1.x.size == 1122, d1.x.size
    assert np.all(np.diff(d1.x) > 0)
    rd = ReflectDataset(os.path.join(_paths()[1], "e361r.txt"))
    assert rd.x.size > 20 and np.all(rd.y_err > 0)
    orso = OrsoDataset(os.path.join(dtests, "ORSO_data.ort"))
    import tempfile
    out = os.path.join(tempfile.mkdtemp(prefix="refnx-orso-"), "roundtrip.ort")
    orso.save(out)
    again = OrsoDataset(out)
    assert again.x.size == orso.x.size, (again.x.size, orso.x.size)
    assert float(abs(again.x - orso.x).max()) == 0.0
    return ("Data1D(dot.out)=%d points, ReflectDataset(e361r)=%d points, "
            "OrsoDataset save/load round-trip exact" % (d1.x.size, rd.x.size))


def _pickle_roundtrip():
    import numpy as np
    structure, q, _ = _structure_and_reference()
    clone = pickle.loads(pickle.dumps(structure))
    dev = float(abs(structure.reflectivity(q) - clone.reflectivity(q)).max())
    assert dev == 0.0, dev
    return "Structure pickle round-trip reproduces the reflectivity exactly"


CHECKS = [
    ("version", _version),
    ("compiled_extensions_loaded", _compiled_extensions_loaded),
    ("cutil_vs_python_reference", _cutil_vs_python_reference),
    ("abeles_matches_motofit_reference", _abeles_matches_motofit_reference),
    ("all_reflect_backends_agree", _all_backends_agree),
    ("abeles_c_vs_pure_python", _abeles_c_vs_pure_python),
    ("parratt_matches_abeles", _parratt_matches_abeles),
    ("abeles_vectorised_equals_scalar", _abeles_vectorised_equals_scalar),
    ("gepore_nonmagnetic_channels", _gepore_nonmagnetic_channels_equals_abeles),
    ("cyreflect_openmp_threads", _cyreflect_openmp_thread_invariance),
    ("structure_reflectivity_kernel", _structure_reflectivity_uses_packaged_kernel),
    ("spline_profile", _spline_profile),
    ("objective_chisqr_nll", _objective_chisqr_and_nll),
    ("curvefitter_fit", _curvefitter_recovers_thickness),
    ("mcmc_posterior", _mcmc_posterior),
    ("dataset_loaders", _dataset_loaders),
    ("pickle_roundtrip", _pickle_roundtrip),
]


def main():
    import argparse
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="", help="write machine-readable counts")
    args = ap.parse_args()
    for name, fn in CHECKS:
        check(name, fn)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    for name, ok, detail in RESULTS:
        print("%s %s %s" % ("PASS" if ok else "FAIL", name, detail))
    print("REFNX_CONSUMER_RESULT discovered=%d passed=%d failed=%d"
          % (len(RESULTS), passed, len(RESULTS) - passed))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"suite": "refnx-consumer", "discovered": len(RESULTS),
                       "passed": passed, "failed": len(RESULTS) - passed,
                       "checks": [{"name": n, "ok": ok, "detail": d}
                                  for n, ok, d in RESULTS]}, fh)
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
