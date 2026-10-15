#!/usr/bin/env python3
"""Conan recipe for spatialite-gui 2.1.0-beta1 — autotools (configure.ac + Makefile.am).

spatialite-gui is the wxWidgets GUI front-end for the SpatiaLite stack. Upstream
configure.ac requires wx-config, geos-config, pg_config, libproj and liblzma
unconditionally; the remaining deps sit behind AC_ARG_ENABLE guards.

Two upstream contracts break on OHOS and are handled here rather than by
patching sources:

1. geos-config / pg_config / wx-config are helper *programs* that configure
   executes and backticks. The Conan packages expose CMake/pkg-config metadata
   instead (geos ships no geos-config; libpq ships pg_config as an ELF helper),
   and HMDFS cannot reliably execute package-cache scripts, so configure gets a
   small locally built ELF stand-in whose answers come from Conan metadata.
   This mirrors the proven libspatialite 5.1.0.2.1 and virtualpg 2.0.1.1
   recipes in this repository.

2. autotools' AC_CHECK_LIB / AC_SEARCH_LIBS probes compile and *run* conftest
   programs. On OHOS every produced executable must carry a code signature or
   execve fails, so each verdict looks like "link failed" and configure bails on
   dependencies that are actually present. configure therefore gets a cc
   wrapper that signs each conftest right after compiling it.

--disable-xlsxwriter is not optional here: libxlsxwriter has no recipe in this
repository (only a stub manifest), and every XLSX code path is #ifdef'd on
ENABLE_XLSXWRITER, so dropping it is a clean, contained degradation. The other
optional codecs are off for the documented per-dependency reasons in notes.md.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps

OHOS = "OHOS"


def _tool(*candidates):
    for candidate in candidates:
        found = shutil.which(candidate) if not os.path.isabs(candidate) else candidate
        if found and os.path.isfile(found):
            return found
    return None


def _c_string(value):
    return value.replace("\\", "\\\\").replace('"', '\\"')


class SpatialiteGuiConan(ConanFile):
    name = "spatialite-gui"
    version = "2.1.0-beta1"
    description = "SpatiaLite GUI — wxWidgets front-end for the SpatiaLite stack"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gaia-gis.it/fossgis/spatialite-gui"
    url = "https://www.gaia-gis.it/gaia-sins/spatialite-gui-sources/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        # G1 requires the standard conandata/patches hand-off: conandata.yml has
        # no patches: section here, so this only stages conandata.yml (and a
        # patches/ dir should one ever be added) for build().
        export_conandata_patches(self)

    def requirements(self):
        # GUI toolkit: provides bin/wx-config (--cxxflags / --libs std,aui).
        self.requires("wxwidgets-gtk3/3.2.10")
        # SpatiaLite core. libspatialite's own notes record --enable-gcp and
        # --enable-rttopo, which configure.ac probes for explicitly via
        # AC_CHECK_LIB(gaiaCreateControlPoints) and
        # AC_CHECK_LIB(gaiaTopoGeo_FromGeoTableNoFaceExtended).
        # 5.1.0.2 (not 5.1.0.2.1): librasterlite2 pins 5.1.0.2, and two exact
        # pins on the same ref abort resolution with a version conflict.
        self.requires("libspatialite/5.1.0.2")
        self.requires("librasterlite2/1.1.0-beta1")
        self.requires("virtualpg/2.0.1.1")
        # curl, not libcurl: that is the package name in this registry, and it
        # exports the libcurl pkg-config name configure probes for.
        self.requires("curl/8.15.0")
        # 3.49.1, not 3.53.4: libspatialite/librasterlite2/virtualpg/proj all
        # pin 3.49.1 — a second exact pin makes the graph abort.
        self.requires("sqlite3/3.49.1")
        # The four below are unconditional upstream deps the task brief did not
        # list: PKG_CHECK_MODULES(liblzma) and AC_SEARCH_LIBS(proj_*) are bare
        # calls with no AC_ARG_ENABLE guard, and geos_c.h / libpq-fe.h are
        # required headers.
        self.requires("liblzma/5.8.1")
        self.requires("proj/9.3.1.1")
        self.requires("geos/3.13.1")
        # 18.1 (not 18.6.1): virtualpg pins libpq/18.1, and two exact pins on
        # the same ref abort resolution with a version conflict.
        self.requires("libpq/18.1")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        self.folders.source = "."

    def source(self):
        # CA fallback is mandatory in recipes that download (AGENTS §1.2): the
        # CI worker has no device-side CA path.
        cert_path = None
        try:
            import certifi

            cert_path = certifi.where()
        except ImportError:
            candidate = os.path.expanduser("~/.conan2/cacert.pem")
            if os.path.isfile(candidate):
                cert_path = candidate
        if not cert_path or not os.path.isfile(cert_path):
            raise ConanInvalidConfiguration(
                "no CA bundle for source download: neither certifi.where() nor "
                "~/.conan2/cacert.pem is available"
            )
        # conan.tools.files.get() takes no cert= parameter (TypeError on
        # 2.29): publish the bundle through the standard env vars instead —
        # OpenSSL's default verify paths (SSL_CERT_FILE) and curl
        # (CURL_CA_BUNDLE) both honour them, and env survives into get().
        if not os.environ.get("SSL_CERT_FILE"):
            os.environ["SSL_CERT_FILE"] = cert_path
        if not os.environ.get("CURL_CA_BUNDLE"):
            os.environ["CURL_CA_BUNDLE"] = cert_path
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # helpers configure executes
    # ------------------------------------------------------------------
    @property
    def _geos_config_path(self):
        return os.path.join(self.build_folder, "geos-config-ohos")

    @property
    def _pg_config_path(self):
        return os.path.join(self.build_folder, "pg_config-ohos")

    @property
    def _cc_wrapper_path(self):
        return os.path.join(self.generators_folder, "sg-conftest-cc.sh")

    @property
    def _sign_events_path(self):
        return os.path.join(self.generators_folder, "sg-conftest-sign-events.txt")

    @property
    def _is_ohos(self):
        return str(self.settings.os) == OHOS

    def _compiler(self):
        executables = self.conf.get("tools.build:compiler_executables", default={},
                                    check_type=dict)
        return executables.get("c", "clang")

    def _write_query_helper(self, out_path, answers):
        """Emit a tiny C program that prints Conan-derived answers for one flag.

        configure runs these helpers and backticks their output, so they must be
        real executables — and on OHOS a signed one.
        """
        os.makedirs(self.build_folder, exist_ok=True)
        source = out_path + ".c"
        lines = [
            "#include <stdio.h>",
            "#include <string.h>",
            "int main(int argc, char **argv) {",
            "  if (argc != 2) return 2;",
        ]
        for flag, answer in answers.items():
            lines.append('  if (!strcmp(argv[1], "%s")) { puts("%s"); return 0; }'
                         % (flag, _c_string(answer)))
        lines += ["  return 2;", "}"]

        with open(source, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")

        self.run('"{}" "{}" -O2 -o "{}"'.format(self._compiler(), source, out_path))
        self._sign_elf(out_path, required=self._is_ohos)

    def _write_geos_config(self):
        """geos-config replacement answering from the geos package layout.

        The flag shapes are asymmetric and configure depends on it:
        configure.ac:168-169 runs
            GEOS_LDFLAGS=`geos-config --ldflags`
            GEOS_CPPFLAGS=-I`geos-config --includes`
        so --includes must print a *bare directory* (configure supplies the
        -I itself) while --ldflags must print -L. Returning "-I<dir>" from
        --includes would yield the broken -I-I<dir>.
        """
        geos = self.dependencies["geos"].cpp_info
        if not geos.includedirs or not geos.libdirs:
            raise ConanInvalidConfiguration("geos package exposes no include/lib dirs")
        self._write_query_helper(self._geos_config_path, {
            "--includes": geos.includedirs[0],
            "--cflags": "-I{}".format(geos.includedirs[0]),
            "--ldflags": "-L{}".format(geos.libdirs[0]),
            "--clibs": "-lgeos_c",
            "--version": "3.13.1",
        })

    def _write_pg_config(self):
        """pg_config replacement: configure only asks for --includedir/--libdir."""
        libpq = self.dependencies["libpq"].cpp_info
        if not libpq.includedirs or not libpq.libdirs:
            raise ConanInvalidConfiguration("libpq package exposes no include/lib dirs")
        self._write_query_helper(self._pg_config_path, {
            "--includedir": libpq.includedirs[0],
            "--libdir": libpq.libdirs[0],
            "--version": "18.6",
        })

    def _write_cc_wrapper(self):
        """Wrap the compiler so every configure conftest is signed before run.

        Without a .codesign section OHOS refuses to exec the probe, so each
        AC_CHECK_LIB verdict reads as "link failed" and configure bails on
        dependencies that are in fact present. Signed paths are appended to
        an evidence file that _validate_conftest_signing then checks, so a
        silently inactive wrapper cannot be mistaken for a passing configure.
        """
        cc = self._compiler()
        objcopy = _tool("llvm-objcopy", "objcopy", "/data/service/hnp/bin/llvm-objcopy")
        signer = _tool("binary-sign-tool", "/data/service/hnp/bin/binary-sign-tool")
        chmod_tool = _tool("chmod", "/system/bin/chmod")
        missing = [name for name, tool in
                   (("objcopy", objcopy), ("binary-sign-tool", signer), ("chmod", chmod_tool))
                   if not tool]
        if missing:
            raise ConanInvalidConfiguration(
                "OHOS conftest signing tools are missing: {}".format(missing)
            )

        script = """#!/system/bin/sh
set -eu
cc={cc}
objcopy={objcopy}
signer={signer}
chmod_tool={chmod_tool}
events={events}
output=a.out
expect_output=0
compile_only=0
for argument in "$@"; do
  if [ "$expect_output" -eq 1 ]; then
    output="$argument"
    expect_output=0
    continue
  fi
  case "$argument" in
    -o) expect_output=1 ;;
    -o?*) output=${{argument#-o}} ;;
    -c|-E|-S) compile_only=1 ;;
  esac
done
"$cc" "$@"
case "$output" in
  /*) ;;
  *) output="$(pwd)/$output" ;;
esac
case "${{output##*/}}" in
  conftest*) ;;
  *) exit 0 ;;
esac
if [ "$compile_only" -ne 0 ] || [ ! -f "$output" ]; then
  exit 0
fi
"$chmod_tool" 755 "$output" 2>/dev/null || true
"$objcopy" --remove-section .codesign "$output" 2>/dev/null || true
"$signer" sign -inFile "$output" -outFile "$output" -selfSign 1
printf '%s\\n' "$output" >> "$events"
exit 0
""".format(cc=cc, objcopy=objcopy, signer=signer, chmod_tool=chmod_tool,
           events=self._sign_events_path)

        os.makedirs(self.generators_folder, exist_ok=True)
        with open(self._sign_events_path, "w", encoding="utf-8", newline="\n") as handle:
            pass
        with open(self._cc_wrapper_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(script)
        os.chmod(self._cc_wrapper_path, 0o755)

    def _validate_conftest_signing(self):
        """Fail loudly if the wrapper signed nothing (AGENTS §8 diagnostic intent).

        configure reporting success with zero signed probes would mean every
        AC_CHECK_LIB verdict was decided on an unsigned executable, so this is
        the one check that distinguishes a real pass from a lucky one.
        """
        if not self._is_ohos:
            return
        try:
            with open(self._sign_events_path, encoding="utf-8") as handle:
                events = [line.strip() for line in handle if line.strip()]
        except OSError as error:
            raise ConanInvalidConfiguration(
                "configure conftest signing evidence is missing"
            ) from error
        if not any(os.path.basename(path).startswith("conftest") for path in events):
            raise ConanInvalidConfiguration(
                "configure produced no signed conftest executable"
            )

    def _drop_unresolvable_cpp_requires(self):
        """PkgConfigDeps resolves every dep's cpp_info.requires entry to
        `pkg::component` and raises when the component does not exist.

        librasterlite2/1.1.0-beta1 publishes
        `cpp_info.requires = [..., "curl::libcurl", ...]`, but the curl recipe
        in this registry declares no components (only
        `pkg_config_name = "libcurl"`), so generator-side resolution dies with
        `Component 'curl::libcurl' not found in the curl package requirement`.

        The entry is cosmetic for this consumer: configure links curl through
        libcurl.pc from our own direct requires, so we only drop entries whose
        target component provably does not exist (and is not an alias of the
        package root).
        """
        for dep in self.dependencies.values():
            requires = list(dep.cpp_info.requires or [])
            if not requires:
                continue
            kept = []
            for req in requires:
                if "::" in req:
                    pkg_name, comp_name = req.split("::", 1)
                    try:
                        target = self.dependencies[pkg_name]
                    except (KeyError, TypeError):
                        kept.append(req)
                        continue
                    components = target.cpp_info.components or {}
                    if comp_name not in components and target.ref.name != comp_name:
                        continue
                kept.append(req)
            if kept != requires:
                dep.cpp_info.requires = kept

    def _resolve_wx_config(self):
        """Path that configure must receive via --with-wxconfig.

        The published wxwidgets-gtk3 package ships `bin/wx-config` as a
        symlink into the *packager's* build cache
        (`~/.cache/conan2/p/b/<build-id>/p`), a path that does not exist on a
        consumer machine — so `os.path.isfile()` reports False, and the
        config script itself prints -I/-L/-.a paths baked from that same
        missing prefix.

        Repair it without touching package content: materialize the baked
        prefix as a symlink to the real package folder, so both the
        bin/wx-config link and every path wx-config prints resolve into the
        shipped package.
        """
        wx_pkg = self.dependencies["wxwidgets-gtk3"].package_folder
        cfg = os.path.join(wx_pkg, "bin", "wx-config")
        if not os.path.isfile(cfg) and os.path.islink(cfg):
            target = os.readlink(cfg)
            if not os.path.isabs(target):
                target = os.path.join(os.path.dirname(cfg), target)
            marker = "/lib/wx/config/"
            if marker in target:
                prefix = target.split(marker, 1)[0]
                if not os.path.isdir(prefix):
                    if os.path.islink(prefix) or os.path.exists(prefix):
                        os.unlink(prefix)
                    os.makedirs(os.path.dirname(prefix), exist_ok=True)
                    os.symlink(wx_pkg, prefix)
        if not os.path.isfile(cfg):
            raise ConanInvalidConfiguration(
                "wxwidgets-gtk3 package has no usable wx-config: {}".format(cfg)
            )
        return cfg

    def _fix_dep_la(self):
        """fix#8: rewrite dependency .la files recorded against an empty prefix.

        librasterlite2/librttopo/libspatialite ship .la files with
        libdir='//lib' and dependency_libs entries like //lib/libspatialite.la
        (their recipes packaged a make install that ran with an empty prefix).
        libtool expands -lrasterlite2 through librasterlite2.la and dies on the
        literal `//lib/libspatialite.la` reference with "cannot find the
        library" (G2 of job -7; job -6 never reached this point because the
        unfiltered -Llib killed libtool first).

        Precedent: DRAFT-ohos-la-libdir-hardcode (speech-dispatcher/0.12.1,
        CI #36976/#37284/#37446/#37458) — copy dependency lib/*.la into a
        staging folder, rewrite libdir= to the real package libdir and the
        empty-prefix .la references to their staging copies, then put
        -L<staging> at the FRONT of LDFLAGS so libtool resolves -l<name>
        through the rewritten copies before reaching the broken originals.
        The flags must ride the configure-time LDFLAGS (baked into the
        Makefile); touching os.environ in build() does nothing (forbid rule 1
        of the draft).

        Difference from the speech-dispatcher regex: a negative lookbehind so
        package-absolute references (.../p/lib/libxxx.la, whose /lib/ is
        preceded by the package id) are left untouched — only empty-prefix
        `//lib/` or standalone `/lib/` .la references are redirected.
        """
        staging = os.path.join(self.build_folder, "ohos-la")
        os.makedirs(staging, exist_ok=True)
        la_dirs = {}
        # fix#9: deps conan marked binary=Skip (statically folded into their
        # consumer, e.g. lz4 into librasterlite2.so) ship no package folder and
        # no library files, yet dependency_libs still lists -l<name> for them
        # (packaging-time residue). Those -l references cannot resolve and
        # ld.lld aborts with "unable to find library". Their symbols are either
        # inlined into the folding .so (nm -D: LZ4_decompress_safe T) or not
        # referenced at all (no unz*/mz_* symbol in librasterlite2.so), so the
        # references are dead and can be dropped. Real system libs
        # (-lpthread/-lm/-ldl) and resolvable conan libs are untouched because
        # their packages have folders / their names never match a Skip dep.
        skip_l_names = set()
        for dependency in self.dependencies.values():
            try:
                has_package = bool(dependency.package_folder)
            except Exception:
                has_package = False
            if not has_package and dependency.ref.name:
                skip_l_names.add(dependency.ref.name)
        skip_l_pattern = ("-l({})(?![\\w.+-])".format(
            "|".join(sorted(re.escape(n) for n in skip_l_names)))
            if skip_l_names else None)
        for dependency in self.dependencies.values():
            try:
                package_folder = dependency.package_folder
            except Exception:
                continue
            if not package_folder:
                continue  # binary=Skip deps have no package folder (fix#7)
            lib_dir = os.path.join(package_folder, "lib")
            if not os.path.isdir(lib_dir):
                continue
            for name in os.listdir(lib_dir):
                if name.endswith(".la"):
                    shutil.copy2(os.path.join(lib_dir, name),
                                 os.path.join(staging, name))
                    la_dirs[name] = lib_dir
        for name in os.listdir(staging):
            path = os.path.join(staging, name)
            if not name.endswith(".la"):
                continue
            with open(path, encoding="utf-8", errors="replace") as handle:
                data = handle.read()
            data = re.sub(r"(?m)^libdir='.*'$",
                          "libdir='{}'".format(la_dirs.get(name, staging)),
                          data, count=1)
            data = re.sub(
                r"(?<![A-Za-z0-9_.-])/{1,2}lib/([A-Za-z0-9_.-]+\.la)",
                lambda match: os.path.join(staging, match.group(1)), data)
            if skip_l_pattern:
                data = re.sub(skip_l_pattern, "", data)
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(data)
        self.output.info(
            "fix#8: rewrote {} dependency .la files into {}".format(
                len(la_dirs), staging))
        return staging

    def generate(self):
        # PkgConfigDeps emits spatialite.pc / rasterlite2.pc / virtualpg.pc /
        # libcurl.pc / libxml-2.0.pc — exactly the PKG_CHECK_MODULES names
        # configure.ac asks for. It also picks up wxwidgets-gtk3's own defines.
        self._drop_unresolvable_cpp_requires()
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # wx-config --libs prints raw -l flags for GTK/glib/zlib/... whose
        # archives live in the conan cache, and wx's own -L only covers the wx
        # prefix — without a search path the final link fails with
        # "library not found for -lgtk-3". Feed every dependency libdir to the
        # linker (AC_CHECK_LIB probes benefit from the same path).
        lib_dirs = []
        for _ref, dependency in self.dependencies.items():
            lib_dirs.extend(dependency.cpp_info.libdirs)
        # fix#8 (2026-10-12): staging copies of the dependency .la files must
        # come FIRST in LDFLAGS — libtool walks -L directories in order when
        # resolving -l<name>, and the rewritten staging .la must be found
        # before the broken libdir='//lib' originals inside the packages.
        # This rides the toolchain LDFLAGS (configure bakes it into the
        # Makefile; os.environ in build() would be too late).
        tc.extra_ldflags.append("-L{}".format(self._fix_dep_la()))
        # fix#7 (2026-10-12): conan 2 marks transitive static deps that the
        # direct dependency already folded into its own static archives as
        # binary=Skip (here: graphite2, folded into static wxWidgets 3.2) and
        # gives them no package folder, so their cpp_info.libdirs stay the
        # relative default "lib". Feeding that into LDFLAGS produces a literal
        # "-Llib" which makes libtool die at link time with
        # "cd: lib: No such file or directory / cannot determine absolute
        # directory name of `lib'" (G2 of job -6). Keep only resolvable
        # absolute directories; a relative libdir carries no usable location.
        lib_dirs = [d for d in dict.fromkeys(lib_dirs) if os.path.isabs(d)]
        for lib_dir in lib_dirs:
            tc.extra_ldflags.append("-L{}".format(lib_dir))
        tc.configure_args.append("--with-wxconfig={}".format(self._resolve_wx_config()))
        tc.configure_args.append("--with-geosconfig={}".format(self._geos_config_path))
        tc.configure_args.append("--with-pgconfig={}".format(self._pg_config_path))

        # Optional features, each with its own reason (see notes.md):
        #  - xlsxwriter: no libxlsxwriter recipe in this repository at all.
        #  - lz4: configure probes the pkg-config name "liblz4", while the
        #    lz4/1.10.0 recipe publishes lz4.pc — the name never matches.
        #  - freexl/minizip/zstd/openjpeg/webp: kept off to hold the linked
        #    surface to what this port actually exercises.
        # libxml2 stays on: virtualpg's .pc and the WFS/KML parsing paths both
        # expect it, and it is already transitive via libspatialite.
        tc.configure_args.extend([
            "--disable-xlsxwriter",
            "--disable-lz4",
            "--disable-freexl",
            "--disable-minizip",
            "--disable-zstd",
            "--disable-openjpeg",
            "--disable-webp",
            "--enable-libxml2",
        ])
        tc.generate()

        env = Environment()
        # configure.ac probes headers directly with AC_CHECK_HEADER
        # (sqlite3.h dies first: "cannot find sqlite3.h, bailing out";
        # geos_c.h / libpq-fe.h are the same class). Those tests compile with
        # $CC $CFLAGS $CPPFLAGS — PKG_CHECK_MODULES-driven .pc flags never
        # reach them, and conan 2.29's AutotoolsToolchain has no cppflags
        # attribute (only defines → -D), so the include dirs go into the
        # build environment instead. AutotoolsToolchain's own script runs
        # first in the aggregate and *appends* its -D defines to CPPFLAGS,
        # so both halves survive.
        include_flags = []
        for _ref, dependency in self.dependencies.items():
            include_flags.extend(
                "-I{}".format(include_dir)
                for include_dir in dependency.cpp_info.includedirs
                if os.path.isdir(include_dir))
        if include_flags:
            env.append("CPPFLAGS", " ".join(dict.fromkeys(include_flags)))
        # fix#2 (2026-10-12): configure:18546 does `LDFLAGS_SAVE="$LDFLAGS";
        # LDFLAGS="$PG_LDFLAGS"` right before the libpq AC_CHECK_LIB probe —
        # a full *override*, not an append — so every -L aggregated into
        # extra_ldflags/LDFLAGS above is gone exactly while the probe links,
        # and ld.lld cannot resolve the PKG_CHECK_MODULES libraries already
        # accumulated in LIBS (-lcurl/-lrasterlite2/-lspatialite/-lproj/
        # -lsqlite3; config.log conftest line keeps only "-L<pq libdir>"
        # and GEOS's -L via LIBS). LDFLAGS is restored right after the probe
        # (LDFLAGS="$LDFLAGS_SAVE") and automake link lines do not carry
        # CPPFLAGS, so the real Makefile link is unaffected. autoconf's
        # ac_link = "$CC $CFLAGS $CPPFLAGS $LDFLAGS conftest.$ac_ext $LIBS"
        # still passes CPPFLAGS, so the same libdir set rides along there and
        # every AC_CHECK_LIB verdict is decided with the full search path.
        if lib_dirs:
            env.append("CPPFLAGS", " ".join(
                "-L{}".format(lib_dir) for lib_dir in dict.fromkeys(lib_dirs)))
        # PkgConfigDeps wrote the .pc files into generators_folder; the five
        # PKG_CHECK_MODULES probes (spatialite/rasterlite2/virtualpg/libcurl/
        # liblzma) only see them if that folder is on PKG_CONFIG_PATH.
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.prepend_path("PATH", "/data/service/hnp/bin")
        env.define("CONFIG_SHELL", "/system/bin/sh")
        env.define("SHELL", "/system/bin/sh")
        # configure's AC_PATH_TOOL(PKG_CONFIG) did not resolve pkg-config from
        # PATH (PKG_CONFIG='' in config.log), so every PKG_CHECK_MODULES probe
        # failed (first hard error: LIBXML2 / libxml-2.0). Pin it explicitly,
        # matching the /data/service/hnp/bin already used above.
        env.define("PKG_CONFIG", "/data/service/hnp/bin/pkg-config")
        # configure must compile its probes through the signing wrapper.
        # conan 2.29's Autotools.configure() accepts only (build_script_folder,
        # args) — there is no `vars=` — so CC is handed over through the build
        # environment instead (the wrapper embeds the real compiler itself, so
        # CC is a single path-free token and needs no quoting).
        env.define("CC", self._cc_wrapper_path)
        env.define("MKDIR_P", "/system/bin/mkdir -p")
        runtime_dirs = []
        for _ref, dependency in self.dependencies.items():
            runtime_dirs.extend(dependency.cpp_info.libdirs)
        # fix#7: same binary=Skip relative-libdir exclusion as LDFLAGS above —
        # a relative "lib" entry would sit unresolved in LD_LIBRARY_PATH too.
        runtime_dirs = [d for d in dict.fromkeys(runtime_dirs)
                        if os.path.isabs(d)]
        if runtime_dirs:
            env.prepend_path("LD_LIBRARY_PATH",
                             ":".join(runtime_dirs))
        # configure executes the helpers and wx-config out of the build folder,
        # so the build folder has to be on PATH.
        env.prepend_path("PATH", self.build_folder)
        # NOTE: the script must NOT be named "conanbuild": conan's env
        # aggregation (generate_aggregated_env) writes the group's aggregate to
        # conanbuild.sh while also listing every script registered under the
        # "build" scope — including ours — so a name collision makes the
        # aggregate source *itself*, recursing forever. Each pass re-prepends
        # PKG_CONFIG_PATH until execve starts failing with E2BIG
        # ("printenv: Argument list too long") and the shell dies with SIGSEGV
        # (conan reports "Error -11 while executing"). A distinct name keeps it
        # a normal member of the same aggregate.
        env.vars(self).save_script("sgui-buildenv")

    def _write_mktemp_shim(self):
        """Shadow PATH's mktemp with a umask-resetting wrapper (fix#3).

        autoconf 2.69 hardcodes `(umask 077 && mktemp -d "./confXXXXXX")`
        into both configure and config.status. The device mktemp is toybox
        (/usr/bin/mktemp -> toybox) and its -d honours the umask: the
        directory lands as 2700 (drwx--S---, owner has no x) and HMDFS then
        refuses writes to it *even for the creating user*, while a post-hoc
        chmod 700 is silently ignored (E046 family) — config.status then dies
        writing subs1.awk, the exact G2 failure of jobs -3/-4. Device probes
        (2026-10-12): umask 002 -> mode 2771 (drwxrws--x, writable), umask
        022 -> 2751 (writable). The shim therefore re-sets umask 002 before
        exec'ing the real mktemp; plain-file mktemp calls keep mode 0600
        because 002 only strips group/other *write* bits a 0600 file does not
        carry.

        The build folder is first on PATH (generate() prepends it last), so
        this shadow wins over /usr/bin/mktemp; the absolute call inside the
        shim avoids self-recursion. Precedents: hyphen-2.8.9 fallback wrapper
        and libvoikko-4.3.3 recipe shims (knowledge drafts). Limitation: GNU
        coreutils mktemp -d ignores the umask (constant 0700) — out of scope
        here, the verify host only ships toybox (notes.md, fix#3).
        """
        os.makedirs(self.build_folder, exist_ok=True)
        path = os.path.join(self.build_folder, "mktemp")
        script = """#!/system/bin/sh
# spatialite-gui recipe shim (fix#3): toybox `mktemp -d` honours the umask,
# so autoconf's "(umask 077 && mktemp -d ./confXXXXXX)" creates an
# unwritable 2700 directory on HMDFS and a later chmod 700 is ignored.
# Reset to 002 so the directory is created 2771 (drwxrws--x, writable).
# Plain mktemp files keep their 0600 mode (002 only strips group/other
# *write* bits, which a 0600 file does not have).
umask 002
exec /usr/bin/mktemp "$@"
"""
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(script)
        os.chmod(path, 0o755)

    def _restore_autotools_script_modes(self):
        """E490 (restore-known-autotools-script-modes): re-add execute bits.

        Adaptation paths that preserve script content do not always preserve
        POSIX execute mode, and G0 flags the unhandled known risk for every
        autotools recipe. Only the five known helper names are touched, only
        where they exist, and only the x bits are OR-ed in (chmod +x
        semantics).
        """
        roots = [self.build_folder]
        if self.source_folder != self.build_folder:
            roots.append(self.source_folder)
        names = ("configure", "config.guess", "config.sub", "install-sh", "missing")
        seen = set()
        restored = 0
        for root in roots:
            for name in names:
                path = os.path.join(root, name)
                if path in seen or not os.path.isfile(path):
                    continue
                seen.add(path)
                mode = os.stat(path).st_mode
                if not mode & 0o111:
                    os.chmod(path, mode | 0o111)
                    restored += 1
                    self.output.info(
                        "E490: restored execute bits on {}".format(path))
        if not restored:
            self.output.info(
                "E490: all known autotools helper scripts already executable")

    def _patch_config_scripts(self):
        """Teach the bundled config.guess/config.sub the HarmonyOS triplet.

        The tarball ships 2009-11-20 config scripts (configure.ac is
        autoconf 2.69 but never refreshes them). On the device
        `uname -s` is "HarmonyOS", so `./config.guess` bails out with
        "cannot guess build type" and configure dies before the first
        check. configure calls BOTH scripts (config.guess for
        $build_alias, then config.sub on its output), so patching only
        one of them still fails: config.sub rejects
        aarch64-unknown-linux-ohos with "machine `aarch64-unknown-linux'
        not recognized" because its KERNEL-OS whitelist has no
        `linux-ohos` entry either (knowledge E007/E268).
        """
        roots = [self.build_folder]
        if self.source_folder != self.build_folder:
            roots.append(self.source_folder)
        seen = set()
        patched = 0
        for root in roots:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if not d.startswith(".git")]
                for name in ("config.guess", "config.sub"):
                    if name not in filenames:
                        continue
                    path = os.path.join(dirpath, name)
                    if path in seen:
                        continue
                    seen.add(path)
                    with open(path, encoding="utf-8", errors="replace") as handle:
                        text = handle.read()
                    original = text
                    if name == "config.guess" and "HarmonyOS" not in text:
                        # 2009 vintage: every branch echoes its answer and
                        # exits directly (there is no GUESS= variable), so the
                        # new arm must do the same. Emitted triplet matches the
                        # device profile (arch=armv8 => aarch64).
                        block = (
                            "    *:HarmonyOS:*:*)\n"
                            "\tcase \"$UNAME_MACHINE\" in\n"
                            "\t    aarch64|arm64) echo aarch64-unknown-linux-ohos; exit ;;\n"
                            "\t    x86_64|amd64)  echo x86_64-unknown-linux-ohos; exit ;;\n"
                            "\t    i?86)          echo i686-unknown-linux-ohos; exit ;;\n"
                            "\t    *)             echo \"$UNAME_MACHINE-unknown-linux-ohos\"; exit ;;\n"
                            "\tesac\n"
                            "\t;;\n")
                        anchor = ("\nesac\n\n"
                                  "#echo '(No uname command or uname output not recognized.)' 1>&2\n")
                        if anchor not in text:
                            self.output.warning(
                                "config.guess: HarmonyOS insertion point not found ({}); "
                                "bundle differs from the tested 2009-11-20 script".format(path))
                        else:
                            text = text.replace(
                                anchor, "\n" + block + anchor[1:], 1)
                    elif name == "config.sub" and "linux-ohos" not in text:
                        # Make "aarch64-unknown-linux-ohos" split into
                        # machine=aarch64-unknown + os=-linux-ohos instead of
                        # machine=aarch64-unknown-linux + os=-ohos.
                        match = re.search(r"\n([ \t]*nto-qnx\* \| linux-gnu\*[^\n]*\n)", text)
                        if not match:
                            self.output.warning(
                                "config.sub: linux-ohos insertion point not found ({})".format(path))
                        else:
                            line = match.group(1)
                            text = text.replace(
                                line, line.replace("linux-gnu*", "linux-gnu* | linux-ohos*", 1), 1)
                    if text != original:
                        with open(path, "w", encoding="utf-8") as handle:
                            handle.write(text)
                        patched += 1
                        self.output.info("patched {}".format(path))
        if not patched:
            self.output.warning(
                "config.guess/config.sub: nothing patched (already HarmonyOS-aware "
                "or scripts absent) — configure will show if that is a problem")

    def build(self):
        # No-op with the current conandata (no patches: key); kept so the patch
        # application point exists and is exercised by G1/CI.
        apply_conandata_patches(self)
        # The helpers must exist before configure runs, and the cc wrapper has
        # to be handed to configure as CC.
        self._write_cc_wrapper()
        self._write_geos_config()
        self._write_pg_config()
        # Must run before configure: without it configure aborts at
        # "cannot guess build type" (2009 config.guess vs uname HarmonyOS).
        self._patch_config_scripts()
        # E490 (fix#4): restore known helper-script execute bits before
        # configure (G0 warned "已知风险 E490 未在配方中处理" on jobs -3/-4).
        self._restore_autotools_script_modes()
        # fix#3 must exist before configure runs: configure AND config.status
        # both resolve mktemp from PATH, and the build folder is first on
        # PATH (generate() prepends it last, after /data/service/hnp/bin).
        self._write_mktemp_shim()

        autotools = Autotools(self)
        autotools.configure()
        self._validate_conftest_signing()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        binary = os.path.join(self.package_folder, "bin", "spatialite_gui")
        if os.path.isfile(binary):
            self._sign_elf(binary, required=self._is_ohos)
        else:
            raise ConanInvalidConfiguration(
                "spatialite_gui binary was not installed into the package"
            )
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Ships an executable, not a library: consumers reach it through the
        # software-level commands.json entry.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

    def _sign_elf(self, path, required=False):
        if not self._is_ohos:
            return
        objcopy = _tool("llvm-objcopy", "objcopy", "/data/service/hnp/bin/llvm-objcopy")
        signer = _tool("binary-sign-tool", "/data/service/hnp/bin/binary-sign-tool")
        if not objcopy or not signer:
            if required:
                raise ConanInvalidConfiguration("OHOS signing tools are missing")
            return
        self.run('"{}" --remove-section .codesign "{}" 2>/dev/null || true'.format(objcopy, path))
        self.run('"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(signer, path, path))
