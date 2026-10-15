#!/usr/bin/env python3
"""test_package for wmauda 0.9 — consumer verification of the installed package.

wmauda is a GTK+2 WindowMaker/Fluxbox dockapp that remote-controls Audacious
over D-Bus.  It is an ``application`` package, so the consumer test drives the
*installed* binary rather than linking a library.

The test logic lives in ``test.sh`` (a test source file, required by CI L0c) so
that the local W3 run and the CI run exercise exactly the same code path:
OHOS ELF shape, no RPATH/RUNPATH, installed pixmaps + man page, the real
DT_NEEDED dependency chain (gtk-x11-2.0 / gdk-x11-2.0 / audclient / glib /
X11), the ``audacious_remote_*`` and ``dbus_g_*`` undefined symbols that prove
the Audacious D-Bus client stub is genuinely linked, the full DT_NEEDED closure
resolvable on OHOS, and one HarmonyOS-specific executed consumer use-case
(launching the dockapp end-to-end; the expected clean refusal "cannot open
display" proves the musl loader resolved the whole chain and GTK+2 init was
reached natively).
"""
import os

from conan import ConanFile


class WmaudaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(self.source_folder, "test.sh")
        # OHOS: /system/bin/sh (mksh) does not execute ELF binaries reliably.
        # Wrap with bash (same approach as the wmtop / swfmill test_packages).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(bash):
            bash = "bash"
        self.run(f'"{bash}" "{script}"', env="conanrun")
