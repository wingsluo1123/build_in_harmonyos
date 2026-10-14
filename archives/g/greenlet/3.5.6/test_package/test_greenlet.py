#!/usr/bin/env python3
"""Consumer-side check for the packaged greenlet 3.5.6 (R34: real API).

This is the consumer-side verification for this package: greenlet is a compiled
C++ extension with **no pure-Python fallback**, so the extension's real behaviour
is asserted end-to-end — importing the module already proves the
``_Py_IsFinalizing`` link issue was solved, and the switching tests prove the
C++ state machine actually works.

The upstream suite (``src/greenlet/tests``) *is* collected and really run by the
recipe (172 items; see MANIFEST.yml / notes.md). It used to be uncollectable
because ``tests/__init__.py`` bare-imported psutil (not on ohpcd, and PF4 forbids
it as a test_requires); that is why two patches make psutil/objgraph optional.
This consumer test remains the primary *deliverable* check: it validates the
packaged artefact rather than the source tree.

Deliberately: no ``__version__``-only check, no print-only stub.
"""
import gc
import os
import sys

if len(sys.argv) > 1:
    sys.path.insert(0, os.path.abspath(sys.argv[1]))

import greenlet as mod
from greenlet import GreenletExit, error, getcurrent, greenlet

pkg_root = os.path.abspath(os.path.dirname(mod.__file__))
assert os.path.basename(pkg_root) == "greenlet", pkg_root

# --- version + exported surface ---------------------------------------------
assert mod.__version__ == "3.5.6", mod.__version__
assert mod.__all__ == ["__version__", "_C_API", "GreenletExit", "error",
                       "getcurrent", "greenlet", "gettrace", "settrace"], mod.__all__
# feature flags compiled into the extension (measured: both are 1 here)
assert getattr(mod, "GREENLET_USE_CONTEXT_VARS", 0) == 1
assert getattr(mod, "GREENLET_USE_GC", 0) == 1
# the C API capsule used by other extensions (e.g. gevent) must be present
assert hasattr(mod, "_C_API")

# --- cooperative switching order --------------------------------------------
# The canonical greenlet ping-pong: control interleaves between two greenlets
# via explicit switch(), and the interleaving order is observable.
order = []
main = getcurrent()


def worker_a():
    order.append("a1")
    b.switch()
    order.append("a2")
    b.switch()


def worker_b():
    order.append("b1")
    a.switch()
    order.append("b2")


a = greenlet(worker_a)
b = greenlet(worker_b)
a.switch()
assert order == ["a1", "b1", "a2", "b2"], order

# --- a greenlet runs its function lazily, not at construction ---------------
lazy = []
g = greenlet(lambda: lazy.append("ran"))
assert lazy == [], "greenlet must not run until switch()"
g.switch()
assert lazy == ["ran"], lazy

# --- getcurrent() inside a greenlet returns that greenlet -------------------
def whoami():
    return getcurrent()


probe = greenlet(whoami)
assert probe.switch() is probe
assert getcurrent() is main

# --- parent chain + run/dead state ------------------------------------------
assert probe.parent is main, "greenlet parent defaults to the creator"
assert probe.dead is True, "finished greenlet should be dead"
assert not bool(probe), "finished greenlet is falsy"

# --- uncaught exception propagates to the caller ----------------------------
def boom():
    raise ValueError("kaboom")

g_err = greenlet(boom)
try:
    g_err.switch()
    raise SystemExit("FAIL: exception did not propagate out of greenlet")
except ValueError as e:
    assert str(e) == "kaboom", e
assert g_err.dead is True

# --- GreenletExit is the cooperative-termination signal ---------------------
def raise_exit():
    raise GreenletExit("bye")
    return "unreachable"  # pragma: no cover

g_exit = greenlet(raise_exit)
# switch() returns the GreenletExit instance rather than propagating it
result = g_exit.switch()
assert isinstance(result, GreenletExit), type(result)
assert g_exit.dead is True

# --- throw() injects an exception into a suspended greenlet -----------------
def yield_once():
    try:
        main.switch("ready")
    except error:
        return "caught"
    return "no-error"

g_throw = greenlet(yield_once)
assert g_throw.switch() == "ready"
assert g_throw.throw(error("injected")) == "caught"

# --- greenlet objects are usable as dict keys / are hashable -----------------
assert isinstance(hash(greenlet(lambda: None)), int)

gc.collect()
print(f"greenlet {mod.__version__} consumer API: PASS ({pkg_root})")
