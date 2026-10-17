#!/usr/bin/env python3
"""Conan recipe - totem-pl-parser 3.26.7 (Meson, GLib playlist/podcast parser).

totem-pl-parser parses playlists (M3U/PLS/XSPF/SMIL/QT/ASX) and podcast feeds
(RSS/Atom).  It is the hard dependency of totem (the GNOME video player).

Build notes (OHOS aarch64):
- gnome.mkenums / gnome.genmarshal need the GLib build tools shipped by the
  glib package (glib-mkenums / glib-genmarshal).  Both are python scripts ->
  wrapped as zero-compile sh launchers and exported through the glib_mkenums /
  glib_genmarshal variables of the generated glib-2.0.pc.  No ELF is produced
  for the wrappers: the worker's SDK lld can lack libxml2.so.16.
- conan_meson_native.ini is patched with absolute tool paths, because the
  worker's python spawns build tools without a PATH lookup.
- introspection / gtk-doc are disabled (no g-ir-scanner / gtkdoc-scan in the
  registry, and no consumer here uses the GIR).
- enable-libgcrypt is off: meson probes libgcrypt with cc.find_library(), which
  cannot see a conan dependency, and that code path only decrypts the dead
  Amazon MP3 store playlist format.
- enable-libarchive is off: the artifact repository's libarchive package does
  not expose its lib directory to a consumer's run environment, so linking it
  yields a library that cannot be resolved at load time (only totem-disc.c ISO
  probing uses it; no upstream test does).
- OHOS shared builds drop the SONAME -> the .so.<soversion> / .so aliases are
  recreated for both libraries.
- The upstream test suite (parser / podcast / disc) runs inside build().  The
  sandbox uid has no /etc/passwd entry and glib's test framework treats the
  resulting getpwuid_r() warning as fatal, so the tests run with a small
  LD_PRELOAD stub answering getpwuid(_r) - that stub exists for the test run
  only, nothing in the package links against it.
"""
import glob
import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class TotemPlParserConan(ConanFile):
    name = "totem-pl-parser"
    version = "3.26.7"
    description = "GObject based playlist and podcast feed parser library"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/totem-pl-parser"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3", transitive_headers=True, transitive_libs=True)
        self.requires("uchardet/0.0.7", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._augment_uchardet_pkg_config()
        tools_folder = self._prepare_glib_build_tools()
        self._augment_glib_pkg_config(tools_folder)
        tc = MesonToolchain(self)
        tc.project_options.update({
            "wrap_mode": "nodownload",
            "default_library": "shared" if self.options.shared else "static",
            "introspection": "false",
            "enable-gtk-doc": "false",
            "enable-uchardet": "yes",
            "enable-libarchive": "no",
            "enable-libgcrypt": "no",
        })
        tc.generate()
        self._inject_meson_tools(tools_folder)

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            if not cross_building(self):
                test_environment = Environment()
                test_environment.define("LD_PRELOAD", self._prepare_passwd_shim())
                with test_environment.vars(self).apply():
                    self._run_upstream_tests()
            else:
                self.output.info("Cross-building: upstream tests are not runnable here")

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        if self.settings.os == "OHOS":
            if self.options.shared:
                self._create_shared_lib_aliases(os.path.join(self.package_folder, "lib"))
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["totem-plparser"]
        self.cpp_info.includedirs = [
            "include/totem-pl-parser/1/plparser",
            "include/totem-pl-parser/1",
            "include",
        ]
        self.cpp_info.set_property("pkg_config_name", "totem-plparser")
        if not self.options.shared and self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ── helpers ────────────────────────────────────────────────────────────
    def _mime_database_available(self):
        """True when a freedesktop MIME database is reachable.

        Two upstream tests (parser/resolution and podcast/image_link) pick a
        parser from the file's MIME type, which needs shared-mime-info.  The
        build machine has none, and the upstream tests say so themselves
        ("is shared-mime-info installed?").
        """
        roots = [
            entry
            for entry in os.environ.get("XDG_DATA_DIRS", "").split(os.pathsep)
            if entry
        ]
        roots.extend(("/usr/local/share", "/usr/share"))
        for root in roots:
            for database in ("mime.cache", "globs2"):
                if os.path.isfile(os.path.join(root, "mime", database)):
                    return True
        return False

    def _test_selection(self):
        if self._mime_database_available():
            return None
        self.output.info(
            "No freedesktop MIME database here: running the MIME-independent "
            "test only - parser/resolution and podcast/image_link need "
            "shared-mime-info to select a parser"
        )
        return ["disc"]

    def _run_upstream_tests(self):
        """Run the upstream suite the way Meson.test() does, but selectable.

        This conan version's Meson.test() accepts no arguments, so the command
        is spelled out here to be able to drop the two tests that need a
        freedesktop MIME database.
        """
        if self.conf.get("tools.build:skip_test", check_type=bool):
            return
        command = f"meson test -v -C {shlex.quote(self.build_folder)}"
        selection = self._test_selection()
        if selection:
            command += " " + " ".join(shlex.quote(name) for name in selection)
        self.run(command)

    def _prepare_passwd_shim(self):
        """Compile the getpwuid(_r) stub used by the upstream test run.

        The build sandbox runs as a uid without an /etc/passwd entry (the same
        limitation recorded for other packages built here) and glib's test
        framework turns the resulting getpwuid_r() warning into a fatal one,
        which kills parser / podcast / disc with SIGTRAP before the first
        assertion runs.  The stub answers the lookup from the environment.
        """
        source_text = r"""
#include <errno.h>
#include <pwd.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>

static int fill_entry(uid_t uid, struct passwd *entry, char *buffer,
                      size_t size, struct passwd **result)
{
    const char *name = getenv("USER");
    const char *home = getenv("HOME");
    const char *tail = "/bin/sh";
    char *cursor = buffer;

    if (!name || !*name)
        name = "ohos";
    if (!home || !*home)
        home = "/";
    if (size < 2 * strlen(name) + strlen(home) + strlen(tail) + 5) {
        if (result)
            *result = NULL;
        return ERANGE;
    }

    entry->pw_name = cursor;
    strcpy(cursor, name);
    cursor += strlen(name) + 1;
    entry->pw_passwd = cursor;
    strcpy(cursor, "x");
    cursor += 2;
    entry->pw_gecos = cursor;
    strcpy(cursor, name);
    cursor += strlen(name) + 1;
    entry->pw_dir = cursor;
    strcpy(cursor, home);
    cursor += strlen(home) + 1;
    entry->pw_shell = cursor;
    strcpy(cursor, tail);
    entry->pw_uid = uid;
    entry->pw_gid = getgid();

    if (result)
        *result = entry;
    return 0;
}

int getpwuid_r(uid_t uid, struct passwd *entry, char *buffer, size_t size,
               struct passwd **result)
{
    return fill_entry(uid, entry, buffer, size, result);
}

struct passwd *getpwuid(uid_t uid)
{
    static struct passwd entry;
    static char buffer[1024];
    struct passwd *result = NULL;

    fill_entry(uid, &entry, buffer, sizeof(buffer), &result);
    return result;
}
"""
        shim_dir = os.path.join(self.build_folder, "test-support")
        os.makedirs(shim_dir, exist_ok=True)
        source = os.path.join(shim_dir, "passwd_shim.c")
        library = os.path.join(shim_dir, "passwd_shim.so")
        with open(source, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(source_text)
        self.run(
            f"{shlex.quote(self._compiler_path('c'))} -shared -fPIC -O1 "
            f"-o {shlex.quote(library)} {shlex.quote(source)}"
        )
        return library

    def _compiler_path(self, language):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get(language)
        if not compiler:
            raise ConanException(
                f"tools.build:compiler_executables carries no '{language}' entry"
            )
        return compiler

    def _build_environment(self):
        environment = Environment()
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        for name in ("TMPDIR", "TMP", "TEMP"):
            environment.define_path(name, tmp)
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        environment.prepend_path("PATH", glib_bin)
        environment.prepend_path("PATH", self._glib_tools_folder())
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        user_bin = os.path.join(os.path.expanduser("~"), ".local", "bin")
        if os.path.isdir(user_bin):
            environment.prepend_path("PATH", user_bin)
        return environment

    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _prepare_glib_build_tools(self):
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)
        for tool in ("glib-mkenums", "glib-genmarshal"):
            source = os.path.join(glib_bin, tool)
            if not os.path.isfile(source):
                raise FileNotFoundError(f"GLib build tool missing: {source}")
            self._build_python_tool_wrapper(tool, source)
        return tools_folder

    def _build_python_tool_wrapper(self, name, script):
        # Zero-compile sh launcher: both GLib tools are python scripts, so the
        # wrapper only redirects them to an absolute interpreter - no ELF and
        # therefore no link step against the SDK lld.
        tools_folder = self._glib_tools_folder()
        wrapper = os.path.join(tools_folder, name)
        python = os.path.realpath(sys.executable)

        def quote(value):
            return "'" + str(value).replace("'", "'\\''") + "'"

        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(f"#!/bin/sh\nexec {quote(python)} {quote(script)} \"$@\"\n")
        os.chmod(wrapper, 0o755)

    def _augment_glib_pkg_config(self, tools_folder):
        pkg_config = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pkg_config):
            raise FileNotFoundError("PkgConfigDeps output is missing: glib-2.0.pc")
        with open(pkg_config, encoding="utf-8") as handle:
            content = handle.read()
        variables = {
            "glib_mkenums": os.path.join(tools_folder, "glib-mkenums"),
            "glib_genmarshal": os.path.join(tools_folder, "glib-genmarshal"),
        }
        variable_block = "".join(
            f"{name}={value.replace(os.sep, '/')}\n"
            for name, value in variables.items()
        )
        # Append -lintl for bindtextdomain()/bind_textdomain_codeset().
        lines = []
        for line in content.splitlines(keepends=True):
            if line.startswith("Libs:") and "-lintl" not in line.split():
                line = line.rstrip("\r\n") + " -lintl\n"
            lines.append(line)
        content = "".join(lines)
        marker = "\nName:"
        if marker not in content:
            raise ValueError("Invalid PkgConfigDeps output: glib-2.0.pc has no Name field")
        content = content.replace(marker, f"\n{variable_block}{marker}", 1)
        with open(pkg_config, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _augment_uchardet_pkg_config(self):
        # Two fixes for the packaged uchardet 0.0.7:
        #  1. the header is installed as include/uchardet/uchardet.h, but the
        #     generated .pc only exposes -I${includedir}, so <uchardet.h> is not
        #     found (the upstream .pc uses -I${includedir}/uchardet).
        #  2. libuchardet.a is a static C++ archive and the C++ runtime it needs
        #     is not declared, so a C target linking it fails with
        #     "undefined symbol: operator new" (this project links with
        #     --no-undefined).  libc++ matches compiler.libcxx=libc++.
        pkg_config = os.path.join(self.generators_folder, "uchardet.pc")
        if not os.path.isfile(pkg_config):
            return
        with open(pkg_config, encoding="utf-8") as handle:
            content = handle.read()
        lines = []
        for line in content.splitlines(keepends=True):
            if line.startswith("Cflags:") and "includedir}/uchardet" not in line:
                line = line.rstrip("\r\n") + ' -I"${includedir}/uchardet"\n'
            elif line.startswith("Libs:") and "-lc++" not in line.split():
                line = line.rstrip("\r\n") + " -lc++\n"
            lines.append(line)
        with open(pkg_config, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("".join(lines))

    def _inject_meson_tools(self, tools_folder):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = ce.get("c") or ""
        compiler_dir = os.path.dirname(compiler) if os.path.sep in compiler else ""

        ar = ce.get("ar")
        ranlib = ce.get("ranlib")
        if compiler_dir:
            if not ar:
                candidate = os.path.join(compiler_dir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
            if not ranlib:
                candidate = os.path.join(compiler_dir, "llvm-ranlib")
                if os.path.isfile(candidate):
                    ranlib = candidate

        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            candidates = [shutil.which("pkg-config")]
            if compiler_dir:
                candidates.append(os.path.join(compiler_dir, "pkg-config"))
            pkg_config = next(
                (path for path in candidates if path and os.path.isfile(path)), None
            )

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            native_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(native_file):
                continue
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue

            binaries = []
            if ar and "\nar =" not in content:
                binaries.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                binaries.append(f"ranlib = '{ranlib}'")
            if (
                pkg_config
                and "\npkg-config =" not in content
                and "\npkgconfig =" not in content
            ):
                binaries.append(f"pkg-config = '{pkg_config}'")
            if not binaries:
                continue
            content = content.replace(
                "[binaries]\n", "[binaries]\n" + "\n".join(binaries) + "\n", 1
            )
            with open(native_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _create_shared_lib_aliases(self, libdir):
        for stem in ("libtotem-plparser", "libtotem-plparser-mini"):
            versioned = sorted(
                path
                for path in glob.glob(os.path.join(libdir, f"{stem}.so.*.*.*"))
                if os.path.isfile(path) and not os.path.islink(path)
            )
            if not versioned:
                continue
            source = versioned[-1]
            soversion = os.path.basename(source).split(".so.")[1].split(".")[0]
            for name in (f"{stem}.so.{soversion}", f"{stem}.so"):
                alias = os.path.join(libdir, name)
                if os.path.lexists(alias):
                    os.unlink(alias)
                shutil.copyfile(source, alias)

    def _sign_installed_elfs(self):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip package signing")
            return
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        candidates = [shutil.which("llvm-objcopy")]
        if cc and os.path.sep in cc:
            candidates.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates if p and os.path.isfile(p)), None)
        patterns = [
            os.path.join(self.package_folder, "bin", "*"),
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ]
        cands = []
        for pattern in patterns:
            cands.extend(glob.glob(pattern, recursive=True))
        for binary in sorted(set(cands)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            if objcopy:
                self.run(
                    f"{shlex.quote(objcopy)} --remove-section .codesign "
                    f"{shlex.quote(binary)} 2>/dev/null || true"
                )
            self._sign_elf(binary)

    def _sign_elf(self, binary):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise FileNotFoundError(f"HarmonyOS binary signer is missing: {signer}")
        self.run(
            shlex.join([
                signer, "sign", "-inFile", binary,
                "-outFile", binary, "-selfSign", "1",
            ])
        )
