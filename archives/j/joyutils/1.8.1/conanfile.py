#!/usr/bin/env python3
"""Conan recipe - joyutils 1.8.1 (plain Makefile, joystick utilities)."""

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
import json
import os
import shutil


class JoyutilsConan(ConanFile):
    name = "joyutils"
    version = "1.8.1"
    description = "jscal, jstest and related utilities for the Linux joystick driver"
    license = "GPL-2.0-only"
    homepage = "https://sourceforge.net/projects/linuxconsole"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "joyutils supports Linux and OHOS, not %s" % self.settings.os
            )

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def _resolve_cc(self):
        # R33: compiler comes from Conan conf first, then env, then PATH.
        # True-machine profiles may point at a stale absolute clang path
        # (preflight: /data/service/hnp/bin/clang missing -> Error 127),
        # so every absolute candidate is existence-checked before use.
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        if isinstance(compilers, str):
            try:
                compilers = json.loads(compilers)
            except ValueError:
                compilers = {}
        if isinstance(compilers, dict) and compilers.get("c"):
            candidates.append(compilers.get("c"))
        try:
            direct = self.conf.get(
                "tools.build:compiler_executables:c", default=None, check_type=str
            )
        except Exception:
            direct = None
        if direct and direct not in candidates:
            candidates.append(direct)
        for key in ("HMBS_CC", "CC"):
            val = os.environ.get(key)
            if val and val not in candidates:
                candidates.append(val)
        for bare in ("clang", "cc", "gcc"):
            if bare not in candidates:
                candidates.append(bare)
        for bare in (
            "aarch64-linux-ohos-clang",
            "aarch64-unknown-linux-ohos-clang",
            "ohos-clang",
        ):
            if bare not in candidates:
                candidates.append(bare)
        # HNP toolchain dir: profile may be stale; pick any present
        # clang-like driver instead of failing on the recorded path.
        try:
            hnp_dir = "/data/service/hnp/bin"
            if os.path.isdir(hnp_dir):
                for entry in sorted(os.listdir(hnp_dir)):
                    low = entry.lower()
                    if "clang" in low or low in ("cc", "gcc", "c99"):
                        full = os.path.join(hnp_dir, entry)
                        if os.path.isfile(full) and full not in candidates:
                            candidates.append(full)
        except OSError:
            pass
        for cand in candidates:
            prog = cand.strip().split()[0] if cand.strip() else ""
            if not prog:
                continue
            if os.path.isabs(prog):
                if os.path.isfile(prog):
                    return cand
                self.output.warning(
                    "joyutils: compiler candidate missing, skipping: %s" % cand
                )
                continue
            if shutil.which(prog):
                return cand
            self.output.warning(
                "joyutils: compiler not on PATH, skipping: %s" % cand
            )
        return "clang"

    def build(self):
        cc = self._resolve_cc()
        self.output.info("joyutils: resolved CC=%s" % cc)
        # Joystick-only build: inputattach and force-feedback (ffmvforce
        # needs SDL2) are disabled, so the recipe has zero Conan
        # dependencies (R36). SYSTEMD_SUPPORT stays off (no libsystemd).
        self.run(
            "make -j1 CC={cc} DISABLE_INPUTATTACH=1 DISABLE_FORCEFEEDBACK=1".format(
                cc=cc
            )
        )

    def _install_file(self, src, dst, mode):
        # cp+chmod replacement for GNU install(1): OHOS ships only a
        # toybox install whose option set rejects the upstream
        # `install -d`/`install -m` invocations (preflight:
        # `install -d <pkg>/bin` -> Makefile:106 Error 64). Python
        # file ops behave identically on Linux and OHOS (E098/E188).
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        try:
            os.chmod(dst, mode)
        except OSError:
            pass

    def _find_utils_file(self, name):
        # Built binaries and generated scripts live in build/utils;
        # static helpers live in both trees; prefer the build tree.
        for base in (
            os.path.join(self.build_folder, "utils"),
            os.path.join(self.source_folder, "utils"),
            self.build_folder,
            self.source_folder,
        ):
            cand = os.path.join(base, name)
            if os.path.isfile(cand):
                return cand
        return None

    def package(self):
        # Manual install (E098/E188): do NOT call `make install` - it
        # shells out to install(1), which OHOS/toybox does not provide
        # with GNU semantics. Layout mirrors utils/Makefile + docs/Makefile
        # install targets with PREFIX empty (bin/, share/joystick/,
        # lib/udev/, share/man/man1/).
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for prog in (
            "jstest",
            "jscal",
            "jscal-restore",
            "jscal-store",
            "evdev-joystick",
        ):
            src = self._find_utils_file(prog)
            if src is None:
                raise ConanInvalidConfiguration(
                    "joyutils: built program missing: %s" % prog
                )
            self._install_file(src, os.path.join(bindir, prog), 0o755)
        joydir = os.path.join(self.package_folder, "share", "joystick")
        os.makedirs(joydir, exist_ok=True)
        for helper in ("extract", "filter", "ident"):
            src = self._find_utils_file(helper)
            if src is None:
                raise ConanInvalidConfiguration(
                    "joyutils: helper script missing: %s" % helper
                )
            self._install_file(src, os.path.join(joydir, helper), 0o755)
        # udev files are harmless on OHOS; keep them for fidelity with
        # the upstream install target.
        udevdir = os.path.join(self.package_folder, "lib", "udev")
        rulesdir = os.path.join(udevdir, "rules.d")
        os.makedirs(rulesdir, exist_ok=True)
        src = self._find_utils_file("js-set-enum-leds")
        if src is not None:
            self._install_file(
                src, os.path.join(udevdir, "js-set-enum-leds"), 0o755
            )
        # 80-stelladaptor-joystick.rules is generated at install time by
        # sed from its .in template with PREFIX empty (upstream:
        # sed "s^@@PREFIX@@^^g"); replicate that generation here.
        rules_in = self._find_utils_file(
            "80-stelladaptor-joystick.rules.in"
        )
        if rules_in is not None:
            with open(rules_in, "r", encoding="utf-8",
                      errors="replace") as f:
                content = f.read()
            content = content.replace("@@PREFIX@@", "")
            rules_out = os.path.join(rulesdir,
                                     "80-stelladaptor-joystick.rules")
            with open(rules_out, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            try:
                os.chmod(rules_out, 0o644)
            except OSError:
                pass
        # Man pages mirror docs/Makefile install target (mode 644).
        mandir = os.path.join(
            self.package_folder, "share", "man", "man1"
        )
        os.makedirs(mandir, exist_ok=True)
        for man in (
            "jstest.1",
            "jscal.1",
            "jscal-restore.1",
            "jscal-store.1",
            "evdev-joystick.1",
        ):
            src = None
            for base in (
                os.path.join(self.build_folder, "docs"),
                os.path.join(self.source_folder, "docs"),
            ):
                cand = os.path.join(base, man)
                if os.path.isfile(cand):
                    src = cand
                    break
            if src is not None:
                self._install_file(
                    src, os.path.join(mandir, man), 0o644
                )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
