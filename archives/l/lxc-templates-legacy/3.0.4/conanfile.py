import os
import glob
import time

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LxctemplateslegacyConan(ConanFile):
    name = "lxc-templates-legacy"
    version = "3.0.4"
    description = "LXC container template scripts - legacy version"
    license = "MIT"
    homepage = "https://linuxcontainers.org/lxc/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # Ensure TMPDIR is set for HMDFS compatibility (E052)
        os.environ.setdefault("TMPDIR", os.path.expanduser("~/tmp"))
        # Apply all patches: pre-generated autotools files are created
        # from /dev/null, so no autoreconf is needed.
        apply_conandata_patches(self)
        self._fix_shebangs()
        self._fix_cross_compile()
        self._fix_configure_tmpdir()
        # Replace missing with no-op to prevent make from regenerating
        # autotools files (which triggers config.status --recheck, E052)
        missing_path = os.path.join(self.source_folder, "missing")
        if os.path.exists(missing_path):
            with open(missing_path, "w") as f:
                f.write("#!/system/bin/sh\nexit 0\n")
            os.chmod(missing_path, 0o755)
        autotools = Autotools(self)
        autotools.configure()
        self._fix_config_status_tmpdir()
        # Normalize timestamps to prevent make from re-running
        # config.status (E052: HMDFS can't create temp files)
        now = time.time()
        for root, dirs, files in os.walk(self.build_folder):
            for fn in files:
                try:
                    os.utime(os.path.join(root, fn), (now, now))
                except OSError:
                    pass
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []

    def _fix_shebangs(self):
        """Fix shebangs for OpenHarmony (E165).

        OpenHarmony has no /bin directory. Replace:
          /bin/sh  -> /system/bin/sh
          /bin/bash -> /data/service/hnp/bin/bash
        """
        replacements = [
            ("#!/bin/sh", "#!/system/bin/sh"),
            ("#! /bin/sh", "#! /system/bin/sh"),
            ("#!/bin/bash", "#!/data/service/hnp/bin/bash"),
            ("#! /bin/bash", "#! /data/service/hnp/bin/bash"),
        ]
        autotools_scripts = [
            "configure", "config.guess", "config.sub",
            "compile", "install-sh", "missing",
        ]
        all_files = [
            os.path.join(self.source_folder, f) for f in autotools_scripts
        ]
        all_files.extend(
            glob.glob(os.path.join(self.source_folder, "templates", "*.in"))
        )
        for path in all_files:
            if not os.path.exists(path):
                continue
            os.chmod(path, 0o755)
            with open(path, "r") as f:
                lines = f.readlines()
            if lines:
                for old, new in replacements:
                    if old in lines[0]:
                        lines[0] = lines[0].replace(old, new)
                        break
            with open(path, "w") as f:
                f.writelines(lines)

    def _fix_cross_compile(self):
        """Fix configure to skip cross-compilation run test.

        OpenHarmony can compile but can't run unsigned test binaries
        during configure's AC_PROG_CC check. Replace the error with
        cross_compiling=no to allow native compilation.
        """
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure_path):
            return
        with open(configure_path, "r") as f:
            content = f.read()
        old = (
            'as_fn_error 77 "cannot run C compiled programs.\n'
            "If you meant to cross compile, use '--host'.\n"
            "See 'config.log' for more details\" \"$LINENO\" 5; }"
        )
        new = 'cross_compiling=no; }'
        content = content.replace(old, new)
        with open(configure_path, "w") as f:
            f.write(content)

    def _fix_config_status_tmpdir(self):
        """Fix config.status temp dir after configure generates it (E052)."""
        tmpdir = os.environ.get("TMPDIR", os.path.expanduser("~/tmp"))
        # Search for config.status in source, build, and subdirectories
        search_dirs = [self.source_folder, self.build_folder]
        for base in search_dirs:
            for root, dirs, files in os.walk(base):
                if "config.status" in files:
                    path = os.path.join(root, "config.status")
                    with open(path, "r") as f:
                        content = f.read()
                    content = content.replace(
                        '"./confXXXXXX"', f'"{tmpdir}/confXXXXXX"')
                    content = content.replace(
                        "./conf$$-$RANDOM", f"{tmpdir}/conf$$-$RANDOM")
                    with open(path, "w") as f:
                        f.write(content)

    def _fix_configure_tmpdir(self):
        """Fix configure to use TMPDIR for temp files (E052: HMDFS).

        HMDFS restricts file creation in auto-generated temp directories.
        Replace ./confXXXXXX with an absolute TMPDIR path so temp files
        go to a writable location.
        """
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure_path):
            return
        tmpdir = os.environ.get("TMPDIR", os.path.expanduser("~/tmp"))
        with open(configure_path, "r") as f:
            content = f.read()
        # Only replace the exact mktemp and fallback patterns
        content = content.replace('"./confXXXXXX"', f'"{tmpdir}/confXXXXXX"')
        content = content.replace("./conf$$-$RANDOM", f"{tmpdir}/conf$$-$RANDOM")
        with open(configure_path, "w") as f:
            f.write(content)
