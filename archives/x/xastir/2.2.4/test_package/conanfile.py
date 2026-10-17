#!/usr/bin/env python3
"""Conan test_package — xastir 2.2.4.

R34 substantive consumer test, twclock precedent:
- (a) functional: ``callpass`` runs natively (pure C, no X) and its APRS
  passcode output is asserted against an independent Python implementation
  of the published hash (0x73e2 seed, pair-wise XOR, 0x7fff mask) — this
  proves the packaged ELF actually executes on the target and computes.
- (b) headless-init negative test: ``xastir`` cannot reach its GUI without
  an X server; the expected result is the real Xt display error and a
  non-zero exit.  Reaching that error requires the dynamic loader to have
  resolved the FULL closure (Motif/Xt/X11/Xext/Xpm + geotiff/tiff/proj +
  curl + xcb/au/dmcp), so it doubles as the runtime-closure evidence.
- (c) ELF DT_NEEDED walk: asserts the direct sonames of the packaged
  binary, covering every platform-critical dependency.
On this host the registry packages for libtiff/libjpeg/libwebp/zstd/libxau/
libxdmcp contain symlink nodes that cannot even be stat()ed (E050); the
consumer stages its own real-file "repair view" of the dependency closure
and prepends it to LD_LIBRARY_PATH, exactly like the recipe build does.
"""
import os
import re
import shutil
from pathlib import Path

from conan import ConanFile


class XastirTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        self._repair_view = self._prepare_repair_view()

    def test(self):
        pkg = self.dependencies["xastir"].package_folder
        bin_dir = os.path.join(pkg, "bin")
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "test_xastir.sh"
        )
        view = str(self._repair_view)
        self.output.info(f"running consumer test: {script} {bin_dir} {readelf}")
        # env="conanrun" supplies LD_LIBRARY_PATH with the packaged
        # Motif/X11/GeoTIFF/curl libs; the repair view goes first so the
        # E050 broken soname links in package dirs are never reached.
        self.run(
            f'sh "{script}" "{bin_dir}" "{readelf}" "{view}"',
            env="conanrun",
        )

    # ---- E050 repair view (mirror of the recipe's linker view) ----------

    def _prepare_repair_view(self):
        view = Path(self.build_folder, "repair-view")
        view.mkdir(parents=True, exist_ok=True)
        broken_found = False
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                source_dir = Path(libdir)
                if not source_dir.is_absolute():
                    source_dir = Path(dependency.package_folder, libdir)
                if not source_dir.is_dir():
                    continue
                for entry in sorted(source_dir.iterdir()):
                    name = entry.name
                    if not (name.endswith(".a") or ".so" in name):
                        continue
                    if name.endswith(".la") or name.endswith(".pc"):
                        continue
                    try:
                        entry_stat = entry.is_file()
                    except OSError:
                        entry_stat = None
                    if entry_stat is None:
                        broken_found = True
                    if self._mirror(entry, source_dir, view):
                        broken_found = broken_found or True
        self.output.info(
            f"E050 repair view: {len(os.listdir(view))} entries "
            f"under {view} (host symlink damage seen: {broken_found})"
        )
        return view

    @staticmethod
    def _mirror(source, source_dir, view):
        destination = view / source.name
        try:
            if source.is_file():
                shutil.copyfile(source, destination)
                return True
        except OSError:
            pass
        if destination.exists() or destination.is_symlink():
            return False
        match = re.match(r"^(.*\.so)(?:\.\d[\w.]*)?$", source.name)
        if not match:
            return False
        stem = match.group(1)
        candidates = []
        for sibling in source_dir.iterdir():
            sibling_match = re.match(
                r"^{stem}\.(\d[\w.]*)$".format(stem=re.escape(stem)),
                sibling.name,
            )
            if not sibling_match:
                continue
            try:
                if sibling.is_file() and not sibling.is_symlink():
                    candidates.append((sibling_match.group(1), sibling))
            except OSError:
                continue
        if candidates:
            candidates.sort(key=lambda item: item[0])
            shutil.copyfile(candidates[-1][1], destination)
            return True
        return False
