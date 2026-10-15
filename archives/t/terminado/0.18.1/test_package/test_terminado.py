#!/usr/bin/env python3
"""Consumer test for terminado/0.18.1 — R34 substantial verification.

terminado is installed as a wheel into the package's site-packages.  The
payload roots are exported as ``*_PACKAGE_ROOT`` variables, so this script
rebuilds the import path from them explicitly instead of trusting the merged
run-environment PYTHONPATH (whose aggregation is order-dependent: a
dependency that uses ``runenv_info.define_path`` can clobber a sibling's
``prepend_path``).

What is actually exercised (no stubs):
  1. ``import terminado`` resolving into THIS package's payload;
  2. ``TermSocket`` / ``TermManagerBase`` — the real public API consumers
     (Jupyter et al.) subclass;
  3. a **real pseudo-terminal** opened through terminado's own
     ``PtyWithClients`` (ptyprocess -> openpty), whose master fd is live;
  4. a command written into the pty is echoed back out of it.

Exit code 0 == the module is loadable and usable on HarmonyOS PC.
"""
import os
import sys


def _payload_path():
    """Rebuild the import path from the exported payload roots."""
    roots = [
        os.environ.get("TERMINADO_PACKAGE_ROOT"),
        os.environ.get("TORNADO_PACKAGE_ROOT"),
    ]
    return [r for r in roots if r]


extra = _payload_path()
if extra:
    sys.path[:0] = extra


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


# --- 1. payload must resolve into this package -----------------------------
root = os.environ.get("TERMINADO_PACKAGE_ROOT")
if not root:
    fail("TERMINADO_PACKAGE_ROOT not exported by package_info()")

import terminado
mod_file = os.path.realpath(terminado.__file__)
if not mod_file.startswith(os.path.realpath(root) + os.sep):
    fail(f"terminado imported from {mod_file}, expected inside {root}")
print(f"PASS: import terminado -> {mod_file}")

# --- 2. public API surface (what real consumers subclass) ------------------
# TermSocket / TermManagerBase / the *Manager classes are top-level exports;
# PtyWithClients lives in terminado.management.  TermSocket's real base class
# is tornado.websocket.WebSocketHandler (terminado/websocket.py:27).
from terminado import TermSocket, TermManagerBase
from terminado.management import PtyWithClients
from tornado.websocket import WebSocketHandler
if not issubclass(TermSocket, WebSocketHandler):
    fail("TermSocket must subclass tornado.websocket.WebSocketHandler")
if not hasattr(TermManagerBase, "get_terminal"):
    fail("TermManagerBase.get_terminal missing")
print("PASS: TermSocket subclasses tornado.websocket.WebSocketHandler; "
      "TermManagerBase.get_terminal present")
# NOTE: PtyWithClients.ptyproc is an *instance* attribute (assigned in
# __init__ via PtyProcessUnicode.spawn), so it is verified on the real
# instance below rather than on the class.

# --- 3. real PTY through terminado's own pty wrapper ----------------------
mgr = TermManagerBase(shell_command=["/bin/sh"])
term = mgr.new_terminal()
master_fd = term.ptyproc.fd
if master_fd < 0:
    fail("ptyprocess returned an invalid master fd")
print(f"PASS: real pty opened via terminado PtyWithClients (master fd={master_fd})")

# --- 4. round-trip through that pty ---------------------------------------
import select
import time

os.write(master_fd, b"echo HELLO_FROM_PTY\n")
buf = b""
deadline = time.time() + 10
while b"HELLO_FROM_PTY" not in buf and time.time() < deadline:
    r, _, _ = select.select([master_fd], [], [], 1.0)
    if r:
        try:
            buf += os.read(master_fd, 4096)
        except OSError:
            break
if b"HELLO_FROM_PTY" not in buf:
    fail(f"no output echoed back through pty, got {buf!r}")
print("PASS: command echoed back through the real pty:", repr(buf))

# --- 5. clean shutdown ----------------------------------------------------
try:
    os.write(master_fd, b"exit\n")
except OSError:
    pass
time.sleep(0.3)
try:
    term.ptyproc.terminate(force=True)
except Exception:
    pass

# --- 6. dependency really resolves into its own payload -------------------
root_t = os.environ.get("TORNADO_PACKAGE_ROOT")
if not root_t:
    fail("TORNADO_PACKAGE_ROOT not exported (tornado dependency missing)")
import tornado
if not os.path.realpath(tornado.__file__).startswith(os.path.realpath(root_t) + os.sep):
    fail(f"tornado imported from {tornado.__file__}, expected inside {root_t}")
print(f"PASS: dependency tornado resolves into {root_t}")

print("\nALL CHECKS PASSED: terminado 0.18.1 is importable and functional on HarmonyOS PC")
