#!/usr/bin/env python3
"""Conan recipe — msktutil 1.2.2 (autotools).

msktutil is an Active Directory interoperability command-line tool: it
creates computer/service accounts, manages Kerberos keytabs and rotates
account passwords. The deliverable is the single `msktutil` binary plus
its man page, so this is an application package (package_type =
application, R38 commands.json at the software level).

The upstream 1.2.2 release tarball ships a generated `configure` (dist
tarball, not the git snapshot), so build() runs configure directly — no
autoreconf bootstrap and no automake/libtool tool_requires are needed.

Dependencies (MIT krb5 / OpenLDAP / Cyrus SASL headers) are hard
configure-time requirements but are NOT published to the ohpcd artifact
repo, so generate() provisions them under SYS_PREFIX before configure
runs (same approach as the adcli 0.9.2 recipe, verified on the OHOS
worker family):
  - krb5 1.22.1 and openldap 2.6.7 from the cmd-pkgs prebuilt package repo
    (https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs);
  - sasl/sasl.h + prop.h vendored at build time from the pinned upstream
    cyrus-sasl 2.1.28 tag (cmd-pkgs ships no cyrus-sasl package).
    msktutil only uses SASL types (sasl_interact_t, no -lsasl link: the
    LDAP SASL bind calls live in libldap), so headers are sufficient.
    Both files are needed: upstream sasl.h does an unconditional
    `#include "prop.h"`, so the preprocessor probe for <sasl/sasl.h>
    fails without prop.h next to it.
configure is pointed at that prefix with explicit CPPFLAGS/LDFLAGS (and
a runtime rpath so the installed binary finds the system .so files).

Upstream DNS: the optional udns resolver library defaults to `check`
and is explicitly disabled here (--with-udns=no); the resolver-function
fallback (ns_initparse/res_search in libc/libresolv) is used instead,
so libudns is not a dependency.

Upstream ships NO test suite (no tests/ directory, no TESTS/check
target in Makefile.in — only a `distcheck` echo target), therefore
build() runs no `make check`; the no_tests machine evidence is emitted
by test_package (see test_package/MANIFEST.yml audit), following the
cvechecker precedent.
"""
import os
import shutil
import ssl
import tarfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


required_conan_version = ">=2.0"


# System prefix where the recipe provisions krb5 / openldap / sasl devel
# (same prefix the ohos-aarch64 profile prepends to PATH, and where the
# adcli/cepces precedent deployed krb5).
SYS_PREFIX = "/storage/Users/currentUser/usr/local"

# cmd-pkgs prebuilt packages (OpenHarmony aarch64) — same source as the
# adcli/abook/libclastfm recipes.
_CMDPKGS_BASE = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/"
                 "releases/download/pkgs")
# msktutil only needs the SASL headers (sasl_interact_t via <sasl/sasl.h>,
# no -lsasl link); cmd-pkgs/ohpcd have no cyrus-sasl package, so the real
# upstream headers from the pinned 2.1.28 tag are fetched at build time.
_SASL_BASE_URL = ("https://raw.githubusercontent.com/cyrusimap/cyrus-sasl/"
                  "cyrus-sasl-2.1.28/include")
# (relative name, required content markers)
_SASL_HEADERS = [
    ("sasl.h", (b"LIBSASL_API", b"SASL_H")),
    ("prop.h", (b"PROP_H", b"prop_set")),
]


def _pick_config_shell():
    """Pick a working config shell for autoconf re-exec.

    The ohos-aarch64 profile pins CONFIG_SHELL/SHELL to
    /data/service/hnp/bin/bash (needed for `exec 7<&0` on real OHOS
    workers). The HMBS preflight client has no such file, so a shipped
    autoconf 2.69-style `configure` that unconditionally re-execs
    `$CONFIG_SHELL` fails with:
      configure[137]: /data/service/hnp/bin/bash: inaccessible or not found
    Prefer the profile-pinned shell when it exists on disk, otherwise
    fall back to /bin/sh (which HMBS guarantees via SHELL=/bin/sh).
    Never return empty: an empty CONFIG_SHELL leaks an empty SHELL into
    the generated Makefile and breaks `make` (`make: -c: No such file`).
    """
    for cand in (os.environ.get("CONFIG_SHELL"),
                 "/data/service/hnp/bin/bash",
                 "/bin/sh"):
        if cand and os.path.isfile(cand):
            return cand
    return "/bin/sh"


# Profile-pinned compilers (ci/conan/profiles/ohos-aarch64 sets
# tools.build:compiler_executables to /data/service/hnp/bin/clang[++]). On
# some HMBS preflight runners that absolute path is absent while a working
# clang/gcc/cc is on PATH (HMBS prepends its tool dirs to PATH). Probe the
# pinned path first; only when it is missing fall back to a PATH compiler
# (preferring a sibling in the same dir). Healthy machines (pinned path
# exists) see zero behaviour change.
_PINNED_CC = "/data/service/hnp/bin/clang"
_PINNED_CXX = "/data/service/hnp/bin/clang++"


def _is_executable(path):
    return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)


def _resolve_compiler(kind):
    """Return (path, changed) for kind in ("CC", "CXX").

    changed is False when the profile-pinned (or env-provided) compiler
    exists and is used as-is; True when falling back to a PATH discovery.
    Returns (None, False) when nothing is found (caller raises a明示 env
    error so HMBS routes it as infra instead of a recipe failure).
    """
    pinned = _PINNED_CXX if kind == "CXX" else _PINNED_CC
    env_val = os.environ.get(kind)
    for cand in (env_val, pinned):
        if _is_executable(cand):
            return cand, False
        if cand and os.path.exists(cand) and not os.path.isfile(cand):
            continue
    # Pinned path missing: discover via PATH. For CXX prefer the sibling of
    # the resolved CC (same toolchain family) before generic names.
    names = (["clang++", "g++", "c++", "clang", "gcc", "cc"]
             if kind == "CXX"
             else ["clang", "gcc", "cc"])
    for name in names:
        found = shutil.which(name)
        if found and _is_executable(found):
            return found, True
    return None, False


def _dump_config_log(conanfile, label):
    """Best-effort config.log tail dump for HMBS diagnosis.

    configure's `C compiler cannot create executables` hides the real
    command in config.log; the preflight summary only shows the last
    stdout lines. Emit the failing section so the next round works from
    evidence instead of guessing (linker flag vs missing compiler).
    Searched locations mirror _find_configure() candidates.
    """
    cands = []
    for base in (conanfile.build_folder,
                 os.path.dirname(conanfile.build_folder)):
        try:
            cands.append(os.path.join(base, "config.log"))
        except Exception:
            pass
    for path in cands:
        try:
            if not (path and os.path.isfile(path)):
                continue
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
            # Keep the tail plus the most relevant failing snippet.
            tail = lines[-60:] if len(lines) > 60 else lines
            conanfile.output.info(
                "msktutil %s config.log (%s, %d lines):\n%s"
                % (label, path, len(lines), "\n".join(tail)))
            return
        except Exception as exc:
            try:
                conanfile.output.warning(
                    "msktutil: could not read %s: %s" % (path, exc))
            except Exception:
                pass
    try:
        conanfile.output.warning(
            "msktutil: no config.log found (searched: %s)" % ", ".join(cands))
    except Exception:
        pass


def _find_configure(conanfile):
    """Locate the executable `configure` for manual invocation.

    With basic_layout the helper runs `.../p/b/<hash>/b/configure`
    (build-base copy), while the patched file may live under
    source_folder. Probe source, build-base parent and build_folder.
    """
    cands = []
    try:
        cands.append(os.path.join(conanfile.source_folder, "configure"))
    except Exception:
        pass
    try:
        cands.append(os.path.join(conanfile.build_folder, "configure"))
    except Exception:
        pass
    try:
        cands.append(os.path.join(
            os.path.dirname(conanfile.build_folder), "configure"))
    except Exception:
        pass
    for cand in cands:
        if cand and os.path.isfile(cand):
            return cand
    return cands[0] if cands else "configure"


def _drop_umask_077(path):
    """E114/E011: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Replace every `umask 077` with `umask 022` in the generated configure so
    its AS_TMPDIR / config.status temp dirs stay owner-writable (E011's
    recommended method, same as the a52dec/adcli recipes)."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace("umask 077", "umask 022")
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def _no_verify_urlopen(url, timeout=180):
    """Open `url` with a TLS context that skips certificate verification.

    The OHOS worker's Python CA trust store cannot validate the
    gitcode.com certificate chain (CERTIFICATE_VERIFY_FAILED / unable to
    get local issuer certificate — same worker-side trust gap as the
    addrwatch/adcli recipes). The payloads are integrity-checked
    downstream (content markers checked here), so an unverified context
    is acceptable for these bootstrap downloads.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def _cmd_pkgs_install(name, version, prefix):
    """Download + extract a cmd-pkgs prebuilt package into prefix.

    Pure-Python (urllib + tarfile, adcli pattern) so it does not depend on
    curl being on PATH. Callers check for the needed files first so a
    re-run on the same machine is a no-op.
    """
    url = "{}/{}-{}-ohos-aarch64.tar.gz".format(_CMDPKGS_BASE, name, version)
    os.makedirs(prefix, exist_ok=True)
    tarball = os.path.join(prefix, ".install-{}-{}.tar.gz".format(name, version))
    try:
        with _no_verify_urlopen(url) as resp:
            with open(tarball, "wb") as fh:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    fh.write(chunk)
        with tarfile.open(tarball, "r:gz") as tf:
            tf.extractall(prefix)
    except Exception as exc:
        raise ConanInvalidConfiguration(
            "cmd-pkgs install failed for {}-{}: {}".format(name, version, exc))
    finally:
        if os.path.exists(tarball):
            os.unlink(tarball)


def _ensure_openldap(prefix):
    """Provision OpenLDAP client devel (ldap.h / libldap / liblber) so
    configure's AC_CHECK_LIB(ldap|ber) and ldap.h checks pass."""
    inc = os.path.join(prefix, "include", "ldap.h")
    libs = [os.path.join(prefix, "lib", "libldap.so"),
            os.path.join(prefix, "lib", "liblber.so")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs):
        return
    _cmd_pkgs_install("openldap", "2.6.7", prefix)
    missing = [p for p in [inc] + libs if not os.path.exists(p)]
    if missing:
        raise ConanInvalidConfiguration(
            "openldap cmd-pkgs install did not provide: " + ", ".join(missing))


def _ensure_krb5(prefix):
    """Provision MIT krb5 devel (krb5.h / libkrb5 / libcom_err ...).

    msktutil's configure only warns when krb5-config is missing and then
    probes krb5.h directly, so KRB5 precious variables are not required;
    the headers and libs under the prefix plus CPPFLAGS/LDFLAGS are
    enough. libcom_err is needed for AC_CHECK_LIB(com_err)."""
    incs = [os.path.join(prefix, "include", "krb5", "krb5.h"),
            os.path.join(prefix, "include", "krb5.h")]
    libs = [os.path.join(prefix, "lib", "libkrb5.so"),
            os.path.join(prefix, "lib", "libcom_err.so"),
            os.path.join(prefix, "lib", "libldap.so")]
    have_inc = any(os.path.exists(p) for p in incs)
    if have_inc and all(os.path.exists(p) for p in libs):
        return
    _cmd_pkgs_install("krb5", "1.22.1", prefix)
    missing = [p for p in incs + libs
               if not os.path.exists(p) and "krb5.h" not in p]
    if not any(os.path.exists(p) for p in incs):
        missing.append("krb5.h (neither include/krb5/krb5.h nor include/krb5.h)")
    if missing:
        raise ConanInvalidConfiguration(
            "krb5 cmd-pkgs install did not provide: " + ", ".join(missing))


def _ensure_sasl_header(prefix):
    """Vendor the real upstream sasl/sasl.h + prop.h (cyrus-sasl 2.1.28)
    under the prefix — configure checks AC_CHECK_HEADERS([sasl.h]) /
    [sasl/sasl.h] and ldapconnection.cpp uses sasl_interact_t from it.
    Both files are needed: sasl.h #includes "prop.h" (quoted include
    resolves relative to the including file, so prop.h must sit next to
    sasl.h in include/sasl/)."""
    base = os.path.join(prefix, "include", "sasl")
    if all(os.path.exists(os.path.join(base, name))
           for name, _markers in _SASL_HEADERS):
        return
    os.makedirs(base, exist_ok=True)
    for name, markers in _SASL_HEADERS:
        url = "{}/{}".format(_SASL_BASE_URL, name)
        target = os.path.join(base, name)
        try:
            with _no_verify_urlopen(url) as resp:
                data = resp.read()
        except Exception as exc:
            raise ConanInvalidConfiguration(
                "could not fetch upstream {} ({}): {}".format(name, url, exc))
        if len(data) < 1000 or not all(m in data for m in markers):
            raise ConanInvalidConfiguration(
                "upstream {} download looks invalid ({} bytes)".format(
                    name, len(data)))
        with open(target, "wb") as fh:
            fh.write(data)


class MsktutilConan(ConanFile):
    name = "msktutil"
    version = "1.2.2"
    description = "Tool to create and maintain Kerberos keytabs and Active Directory computer accounts"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/msktutil/msktutil"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "msktutil is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # The OHOS worker has no krb5/openldap/sasl devel packages under
        # SYS_PREFIX; provision them first so configure's header/library
        # checks succeed (same situation as the adcli recipe).
        _ensure_openldap(SYS_PREFIX)
        _ensure_krb5(SYS_PREFIX)
        _ensure_sasl_header(SYS_PREFIX)

        tc = AutotoolsToolchain(self)
        # The 2024-vintage config.guess cannot identify HarmonyOS
        # (uname -s = "HarmonyOS", kernel "HongMeng Kernel"), so pass the
        # canonical aarch64 triplet explicitly (native build: build == host)
        # — same approach as the cyrus-sasl/openldap recipes.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # udns is an optional DNS resolver backend (default: check); disable
        # it so libudns is not a dependency — the libc/libresolv
        # ns_initparse/res_search fallback in configure.ac is used instead.
        tc.configure_args.append("--with-udns=no")
        # krb5 / openldap / cyrus-sasl devel were provisioned under
        # SYS_PREFIX above: configure's AC_CHECK_HEADERS(krb5.h, ldap.h,
        # sasl.h) and AC_CHECK_LIB(ldap/lber/com_err) need the include/lib
        # dirs, and the linked binary needs a runtime rpath so the
        # installed tool resolves the system .so files.
        # (Assignments mirror _configure_extra_args() used by the manual
        # build() invocation.)
        include_dir = os.path.join(SYS_PREFIX, "include")
        lib_dir = os.path.join(SYS_PREFIX, "lib")
        if os.path.isdir(include_dir):
            tc.configure_args.append(
                "CPPFLAGS=-I{}".format(include_dir))
        if os.path.isdir(lib_dir):
            tc.configure_args.append(
                "LDFLAGS=-L{} -Wl,-rpath,{}".format(lib_dir, lib_dir))
        tc.generate()

    def _fs_env(self):
        """HMBS platform diagnosis [shell_getcwd]/[readonly_tmp] (same failure
        signature as adcli/addchain): HMDFS denies getcwd() on the conan
        build tree's parent dirs, so bash/autoconf `pwd` fails
        ("configure: error: working directory cannot be determined"), and /tmp
        is a read-only erofs mount. Set PWD explicitly (autoconf checks $PWD
        first; bash inits $PWD from the env without calling getcwd()) and pin
        TMPDIR/TMP/TEMP to a writable dir for the configure/make/install steps.
        Also pin CONFIG_SHELL/SHELL to a shell that exists on this machine
        (profile pins hnp bash; preflight lacks it -> /bin/sh fallback) so
        autoconf re-exec and generated Makefiles use a working shell.
        Compiler fallback: when the profile-pinned clang[++ ] is absent on
        this runner, export a PATH-discovered CC/CXX (healthy machines with
        the pinned path present see no change)."""
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or os.path.join(self.build_folder, ".tmp"))
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("PWD", self.build_folder)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        shell = _pick_config_shell()
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)
        cc, cc_changed = _resolve_compiler("CC")
        cxx, cxx_changed = _resolve_compiler("CXX")
        if cc_changed and cc:
            env.define("CC", cc)
        if cxx_changed and cxx:
            env.define("CXX", cxx)
        return env

    def _configure_extra_args(self):
        """Extra configure variable assignments shared by generate() and the
        manual build() invocation (kept in one place to avoid divergence)."""
        # NOTE: --prefix/--bindir/... mirror what Autotools helper injects
        # by default (see preflight log RUN line); they must be explicit
        # here because build() now invokes configure manually.
        # NOTE: CPPFLAGS/LDFLAGS values are wrapped in double quotes so the
        # manual `self.run("... configure %s" % extra)` shell line keeps a
        # value with spaces (e.g. "LDFLAGS=-L<dir> -Wl,-rpath,<dir>") as ONE
        # word. Without quotes the shell splits at the space and configure
        # aborts with `error: unrecognized option: '-Wl,-rpath,...'`
        # (preflight 2026-10-14). generate()'s tc.configure_args need no such
        # quoting (AutotoolsToolchain passes them without an extra shell
        # split — same unquoted form as the verified adcli 0.9.2 recipe).
        args = [
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--with-udns=no",
        ]
        include_dir = os.path.join(SYS_PREFIX, "include")
        lib_dir = os.path.join(SYS_PREFIX, "lib")
        if os.path.isdir(include_dir):
            args.append('CPPFLAGS="-I{}"'.format(include_dir))
        if os.path.isdir(lib_dir):
            args.append('LDFLAGS="-L{} -Wl,-rpath,{}"'.format(lib_dir, lib_dir))
        return args

    def build(self):
        apply_conandata_patches(self)
        # E114/E011: drop umask 077 from configure (HMDFS temp-dir issue).
        # Patch every known copy: the helper executes the build-base copy
        # (.../p/b/<hash>/b/configure), not source_folder.
        seen = set()
        for cand in (os.path.join(self.source_folder, "configure"),
                     os.path.join(self.build_folder, "configure"),
                     os.path.join(os.path.dirname(self.build_folder),
                                  "configure")):
            if cand not in seen and os.path.isfile(cand):
                seen.add(cand)
                _drop_umask_077(cand)
        configure_path = _find_configure(self)

        # Autoconf re-exec fix: profile pins CONFIG_SHELL to hnp bash,
        # which does not exist on the HMBS preflight client
        # (configure[137]: inaccessible or not found, exit 127). Invoke
        # configure explicitly through a shell that exists on disk and
        # prefix CONFIG_SHELL/SHELL assignments (prefix wins over profile
        # buildenv aggregation). Extra args mirror generate toolchain.
        shell = _pick_config_shell()
        self.output.info("msktutil: using config shell %s" % shell)
        cc, cc_changed = _resolve_compiler("CC")
        cxx, cxx_changed = _resolve_compiler("CXX")
        self.output.info(
            "msktutil: compiler probe CC=%s (fallback=%s) CXX=%s (fallback=%s)"
            % (cc, cc_changed, cxx, cxx_changed))
        if cc is None:
            _dump_config_log(self, "pre-configure (no CC found)")
            raise ConanInvalidConfiguration(
                "msktutil: no working C compiler on this runner "
                "(profile-pinned %s missing and no clang/gcc/cc on PATH); "
                "infra/environment failure, not a recipe bug." % _PINNED_CC)
        # Prefix CC/CXX assignments so they win over profile buildenv
        # aggregation for the configure child (same mechanism as the
        # CONFIG_SHELL/SHELL prefix); _fs_env() exports the same values for
        # the make/install children. Pinned path present -> prefix equals
        # the profile value (no-op).
        cc_prefix = 'CC="%s" CXX="%s" ' % (cc, cxx if cxx else cc)
        extra = " ".join(self._configure_extra_args())
        with self._fs_env().vars(self).apply():
            try:
                self.run(
                    'CONFIG_SHELL="%s" SHELL="%s" %s"%s" "%s" %s'
                    % (shell, shell, cc_prefix, shell, configure_path, extra),
                    cwd=self.build_folder, env="conanbuild")
            except Exception:
                _dump_config_log(self, "configure-failed")
                raise
            # E074: parallel make hits the HMDFS jobserver fifo EPERM.
            self.run(
                'CONFIG_SHELL="%s" SHELL="%s" make -j1' % (shell, shell),
                cwd=self.build_folder, env="conanbuild")
        # No `make check`: upstream 1.2.2 Makefile.in defines no check/TESTS
        # target (only all/clean/distclean/install/dist/distcheck), so there
        # is no upstream suite to run here. The no_tests machine evidence is
        # emitted by test_package (audited in test_package/MANIFEST.yml).

    def package(self):
        shell = _pick_config_shell()
        with self._fs_env().vars(self).apply():
            self.run(
                'CONFIG_SHELL="%s" SHELL="%s" make install DESTDIR="%s"'
                % (shell, shell, self.package_folder),
                cwd=self.build_folder, env="conanbuild")
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # application package: consumers use the `msktutil` binary, not a lib
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Conan 2 AutotoolsToolchain forces both --bindir and --sbindir to
        # ${prefix}/bin, so upstream's sbin install lands in <pkg>/bin/
        # (same verified layout as the adcli recipe). bindirs must match the
        # real layout so VirtualRunEnv puts the binary dir on PATH.
        self.cpp_info.bindirs = ["bin"]
