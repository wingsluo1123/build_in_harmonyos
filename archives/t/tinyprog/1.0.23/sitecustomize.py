"""HarmonyOS compatibility shim for pyserial's serial-port enumeration.

CPython imports this module automatically at start-up (through ``site``)
whenever the directory that holds it is on ``sys.path`` — here the tinyprog
package root, which Conan's run environment puts on ``PYTHONPATH``.  Shipping
the shim alongside the payload therefore covers the CLI, ``test_package`` and
any consumer that imports this package.

pyserial 3.5 picks its ``serial.tools.list_ports`` backend from ``os.name`` and
then lets ``serial.tools.list_ports_posix`` select the platform implementation
from ``sys.platform``.  That module only recognises the prefixes it was written
for (``linux``, ``darwin``, ``cygwin``, …) and raises ``ImportError`` for
anything else.  The HarmonyOS PC runtime reports ``sys.platform`` as ``'ohos'``
on some builds (``'harmonyos'`` / ``'ohos-*'`` on others), so ``import
tinyprog`` dies at ``from serial.tools.list_ports import comports`` before any
tinyprog code runs.

Registering the Linux implementation under the name pyserial's dispatcher looks
for makes that import resolve to a working backend on OHOS.  The shim is a
no-op on every other platform.
"""

import sys

if sys.platform.startswith(("ohos", "harmonyos")):
    try:
        from serial.tools import list_ports_linux as _list_ports_linux
    except ImportError:
        # pyserial is not importable from this interpreter; nothing to fix.
        pass
    else:
        sys.modules.setdefault(
            "serial.tools.list_ports_posix", _list_ports_linux)
