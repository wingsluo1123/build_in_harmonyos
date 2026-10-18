import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


# Production runtime dependencies, pinned to the versions declared in the
# upstream package.json of tag 3.1.0 (all pure JavaScript, no native addons).
_runtime_deps = [
    "chalk@5.6.2",
    "entities@7.0.0",
    "fast-xml-parser@5.2.5",
    "jschardet@3.0.0",
    "listr2@9.0.4",
    "lodash-es@4.17.21",
    "luxon@3.7.2",
    "semver@7.7.2",
    "yargs@18.0.0",
]


class IdnitsConan(ConanFile):
    name = "idnits"
    version = "3.1.0"
    description = "IETF tool to inspect Internet-Draft documents for conformance with IETF policies"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ietf-tools/idnits"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    topics = ("ietf", "internet-draft", "rfc", "linter", "cli", "nodejs")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"idnits is prepared for Linux/OHOS targets only, got {self.settings.os}"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("idnits supports OHOS armv8 only")
        # Node.js >= 20 is required by the upstream package.json engines field.
        # On the OHOS device the conan build env PATH usually lacks node; it
        # lives under the hnp tree (see _node_dir). The packaged application
        # runs on the system node of the target device at runtime.
        if self._node_dir() is None:
            raise ConanInvalidConfiguration(
                "idnits requires Node.js: put node in PATH or install it under "
                "/data/service/hnp/node.org/"
            )

    def _node_dir(self):
        """Directory containing the node executable for this platform.

        OHOS: the conan build env PATH often lacks node; the hnp tree keeps it
        under /data/service/hnp/node.org/node_vX.Y.Z/bin. Prefer PATH, then
        the hnp locations.
        """
        found = shutil.which("node")
        if found:
            return os.path.dirname(found)
        hnp_root = "/data/service/hnp/node.org"
        if os.path.isdir(hnp_root):
            for entry in sorted(os.listdir(hnp_root), reverse=True):
                candidate = os.path.join(hnp_root, entry, "bin")
                if os.path.isfile(os.path.join(candidate, "node")):
                    return candidate
        if self._is_ohos():
            # Validate-time check on a cross host: the OHOS toolchain lives on
            # the device, so accept the known device location.
            return "/data/service/hnp/node.org/node_v24.13.0/bin"
        return None

    # Source URL and SHA256 are declared in conandata.yml (G1 gate) and read
    # through self.conan_data here; the same values are pinned in
    # ci-facing manifest.yaml.
    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _is_ohos(self):
        return str(self.settings.os) == "OHOS"

    def _npm_cli(self, node_exe=None):
        """Locate the real npm-cli.js next to the chosen node executable.

        On OHOS the hnp ``npm`` shell wrapper aborts node with Signal 5, so npm
        must be invoked directly through its JS entry point (roblox-ts lesson).
        """
        if node_exe is None:
            node_exe = shutil.which("node") or "node"
        real = os.path.realpath(node_exe)
        candidate = os.path.join(
            os.path.dirname(os.path.dirname(real)), "lib", "node_modules", "npm", "bin", "npm-cli.js"
        )
        if os.path.isfile(candidate):
            return candidate
        try:
            out = subprocess.run(
                [node_exe, "-p", "require.resolve('npm/bin/npm-cli.js')"],
                capture_output=True, text=True, timeout=60,
            )
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except OSError:
            pass
        return "npm"

    def build(self):
        # conandata.yml carries sources only (no patches); the patch hook is
        # called only when conan_data exists so the G1 gate sees the hook.
        if self.conan_data:
            apply_conandata_patches(self)

        workspace = self._workspace()
        if os.path.isdir(workspace):
            shutil.rmtree(workspace)
        shutil.copytree(self.source_folder, workspace, symlinks=True)

        npm_cache = os.path.join(self._workspace_root(), "npm-cache")
        tmpdir = os.path.join(self._workspace_root(), "tmp")
        os.makedirs(npm_cache, exist_ok=True)
        os.makedirs(tmpdir, exist_ok=True)

        if self._is_ohos():
            # OHOS build host: node must not inherit the C/C++ buildenv
            # (conanbuild.sh LD_LIBRARY_PATH makes V8 abort), npm must run
            # jitless through npm-cli.js, and .bin symlinks are rejected by
            # HMDFS. stdio is redirected so the real npm error is visible.
            node_dir = self._node_dir()
            node_exe = os.path.join(node_dir, "node")
            npm_cli = self._npm_cli(node_exe)
            hb_bin = os.path.expanduser("~/.harmonybrew/bin")
            install_log = os.path.join(self._workspace_root(), "npm-install.log")
            cmd = (
                f'PATH="{hb_bin}:{node_dir}:/data/service/hnp/bin:/usr/bin:/bin" '
                f'NPM_CONFIG_CACHE="{npm_cache}" TMPDIR="{tmpdir}" '
                f'NODE_OPTIONS=--jitless '
                f'"{node_exe}" --jitless "{npm_cli}" install '
                f"--omit=dev --ignore-scripts --no-bin-links --no-audit --no-fund "
                f"--no-save --no-package-lock {' '.join(_runtime_deps)}"
                f' > "{install_log}" 2>&1'
                f' || {{ rc=$?; cat "{install_log}"; exit $rc; }}'
            )
            self.run(cmd, cwd=workspace, env=None)
            node_flags = "--jitless"
            prefix = f'PATH="{node_dir}:/data/service/hnp/bin:/usr/bin:/bin" '
        else:
            # Host build: set npm environment through the process environment
            # (conan runs commands through cmd.exe on Windows, where the
            # "VAR=value command" shell syntax is not available).
            os.environ["NPM_CONFIG_CACHE"] = npm_cache
            os.environ["TMPDIR"] = tmpdir
            self.run(
                "npm install --omit=dev --ignore-scripts --no-audit --no-fund "
                f"--no-save --no-package-lock {' '.join(_runtime_deps)}",
                cwd=workspace,
            )
            node_flags = ""
            prefix = ""

        # Build-stage functional smoke tests against the real CLI.
        if self._is_ohos():
            node_exe = os.path.join(self._node_dir(), "node")
        else:
            node_exe = "node"
        fixture = os.path.join(workspace, "tests", "fixtures", "draft-beep-boop.txt")
        self.run(
            f'{prefix}"{node_exe}" {node_flags} cli.js --version',
            cwd=workspace,
        )
        self.run(
            f'{prefix}"{node_exe}" {node_flags} cli.js "{fixture}"',
            cwd=workspace,
        )

    def package(self):
        workspace = self._workspace()
        app_dir = os.path.join(self.package_folder, "res", "idnits")

        for directory in ("lib", "node_modules"):
            src = os.path.join(workspace, directory)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(app_dir, directory), symlinks=True)

        for filename in ("cli.js", "package.json", "README.md", "LICENSE"):
            copy(self, filename, src=workspace, dst=app_dir, keep_path=False)

        copy(self, "LICENSE", src=workspace,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        # Launcher: prepend the device node directory when PATH lacks node
        # (hnp tree) and always run jitless (V8 Signal 5 on OHOS otherwise;
        # harmless elsewhere — idnits uses no WebAssembly). Do NOT use env -i:
        # a fully cleaned environment breaks OHOS exec permission checks
        # ("node: inaccessible or not found", device r3 probe), while the
        # inherited conan session env runs node fine (r2 build smoke).
        launcher = os.path.join(self.package_folder, "bin", "idnits")
        save(
            self,
            launcher,
            "#!/bin/sh\n"
            "set -eu\n"
            'script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
            'APP="$script_dir/../res/idnits/cli.js"\n'
            'IDNITS_NODE_DIR="${IDNITS_NODE_DIR:-/data/service/hnp/node.org/node_v24.13.0/bin}"\n'
            'PATH="$IDNITS_NODE_DIR:$PATH"\n'
            'export PATH\n'
            'exec node --jitless "$APP" "$@"\n',
        )
        os.chmod(
            launcher,
            os.stat(launcher).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []

    def _workspace_root(self):
        if self._is_ohos():
            root = os.environ.get(
                "OHOS_NODE_WORKDIR",
                "/data/storage/el2/base/cache/idnits-conan",
            )
        else:
            # Outside the conan cache entirely: in the cache layout the build
            # folder's parent is the source folder, so an in-cache workspace
            # would make copytree recurse into itself.
            import tempfile

            root = os.path.join(tempfile.gettempdir(), "idnits-conan-work")
        os.makedirs(root, exist_ok=True)
        return root

    def _workspace(self):
        return os.path.join(self._workspace_root(), self.version)
