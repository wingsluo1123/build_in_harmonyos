#!/usr/bin/env python3
"""Conan recipe — imagination 3.6 (GTK+3 slideshow maker, Autotools application).

HarmonyOS PC (aarch64) adaptation notes:

* The Debian orig tarball ships a pre-generated configure + Makefile.in
  tree, so no autoreconf bootstrap is needed (unlike l3afpad). The shipped
  config.guess/config.sub (2020-01) predate HarmonyOS and are replaced at
  build time with self-contained OHOS-aware scripts (aris/2.2 precedent).
* configure.ac hard-requires sox >= 14.2.0 (unconditional
  PKG_CHECK_MODULES(SOX)) for the audio import/export pipeline, but the
  ohpcd Conan remote publishes no sox package. Audio support is disabled
  cleanly at build time via a self-contained no-op stub: generate() writes
  a stub sox.h + sox.pc (empty Libs) and prepends the stub dir to
  PKG_CONFIG_PATH. sox_open_read()/sox_open_write() always return NULL,
  which every caller treats as "cannot open this audio file": audio files
  never enter the GUI list (img_get_audio_length() -> NULL ->
  img_add_audio_files() skips), the sox export thread is never spawned
  (img_prepare_audio() sees an empty list and takes the "-an" branch), and
  the effect-chain entry points are never reached. No upstream .c source
  is modified for this.
* The doc/ subdirectory (DocBook HTML manuals) is dropped from SUBDIRS:
  its XSL stylesheet imports
  http://docbook.sourceforge.net/release/xsl/... which xsltproc resolves
  over the network at build time - neither available nor desired in the
  CI sandbox.
* configure runtime fixes (0001): "CFLAGS=\"-g -Wall\"" clobbered the
  conan-injected cross flags -> "$CFLAGS -g -Wall"; the XML::Parser perl
  probe is skipped (only intltool-merge's desktop mode, which is pure
  text processing, is exercised - intltool/0.51.0 recipe precedent);
  config.status's `umask 077` temp dirs are unwritable on the setgid
  hmdfs volume -> 022 (l3afpad/intltool precedents).
* The final link hardcodes -lgmodule-2.0 (plugin loader), and glib's
  gi18n.h maps gettext() to g_libintl_* aliases that live in glib's
  private libintl; glib's generated .pc files propagate neither. Both are
  appended through make's own LIBS variable together with glib's libdir
  (l3afpad precedent - passing them to configure would break AC_PROG_CC's
  conftest with "C compiler cannot create executables").
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

_SOX_STUB_PC = """\
Name: sox
Description: no-op libsox stub - audio support disabled in the imagination HarmonyOS PC build
Version: 14.4.2
Cflags: -I{include_dir}
Libs:
"""

_SOX_STUB_H = """\
/*
 * Minimal no-op libsox stub for the HarmonyOS PC build of imagination 3.6.
 *
 * imagination's configure.ac unconditionally requires sox >= 14.2.0 for its
 * audio import/export pipeline, but no sox package is published for this
 * platform. This self-contained header (paired with a stub sox.pc whose
 * Libs: line is empty) keeps the build compiling and linking with the audio
 * subsystem disabled:
 *
 *  - sox_open_read()/sox_open_write() always return NULL - the documented
 *    "cannot open this audio file" signal. Every caller guards on it:
 *    audio files never enter the GUI list, the sox worker thread is never
 *    spawned and video export takes the "-an" (no audio) ffmpeg branch.
 *  - The effect-chain entry points are no-ops; the thread that would drive
 *    them is never started, so they are unreachable at runtime.
 *
 * This is NOT a functional libsox replacement and must not be reused as
 * one; it exists solely so imagination remains buildable while sox is
 * unavailable on OHOS.
 */
#ifndef IMAGINATION_SOX_STUB_H
#define IMAGINATION_SOX_STUB_H

#include <stdarg.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef long sox_sample_t;

typedef enum { sox_false = 0, sox_true = 1 } sox_bool;

/* SOX_LIB_VERSION_CODE != SOX_LIB_VERSION(14,2,0), so imagination's
 * version guard selects the modern 3-argument sox_flow_effects() shape. */
#define SOX_LIB_VERSION(a, b, c) (((a) << 16) | ((b) << 8) | (c))
#define SOX_LIB_VERSION_CODE SOX_LIB_VERSION(14, 4, 2)

#define SOX_SUCCESS 0
#define SOX_EOF (-1)
#define SOX_EFF_MCHAN 0x0008u

/* Stub encoding holders: only ever address-taken or passed as NULL. */
typedef struct { int encoding; } sox_encoding_t;
typedef struct { int encoding; } sox_encodinginfo_t;

typedef struct {
    double   rate;
    unsigned channels;
    size_t   length;
    unsigned precision;
} sox_signalinfo_t;

typedef struct {
    sox_signalinfo_t signal;
    sox_encoding_t   encoding;
} sox_format_t;

/* imagination only touches effp->out_signal.channels (input_drain). */
typedef struct sox_effect_s {
    sox_signalinfo_t out_signal;
} sox_effect_t;

typedef void sox_flow_effects_callback(sox_bool all_done, void *client_data);

/* Field order matches the real libsox handler so the aggregate
 * initializers in src/img_sox.c compile unchanged. */
typedef struct sox_effect_handler_s {
    const char *name;
    const char *usage;
    unsigned long flags;
    int (*getopts)(sox_effect_t *effp, int argc, char **argv);
    int (*start)(sox_effect_t *effp);
    int (*flow)(sox_effect_t *effp, sox_sample_t const *ibuf,
                sox_sample_t *obuf, size_t *isamp, size_t *osamp);
    int (*drain)(sox_effect_t *effp, sox_sample_t *obuf, size_t *osamp);
    int (*stop)(sox_effect_t *effp);
    int (*kill)(sox_effect_t *effp);
    size_t priv_size;
} sox_effect_handler_t;

/* Opaque: imagination only passes pointers around. */
typedef struct sox_effects_chain_s sox_effects_chain_t;

/* sox_globals is assigned once in main() and never read afterwards (the
 * reader would be libsox itself, which is absent); a per-TU static keeps
 * that assignment legal without introducing a link-time definition. */
typedef struct {
    void (*output_message_handler)(unsigned level, const char *filename,
                                   const char *fmt, va_list ap);
} sox_globals_t;
static sox_globals_t sox_globals;

static inline void sox_format_init(void)
{
}

static inline void sox_format_quit(void)
{
}

static inline sox_format_t *sox_open_read(char const *path,
                                          sox_signalinfo_t const *signal,
                                          sox_encodinginfo_t const *encoding,
                                          char const *filetype)
{
    (void)path; (void)signal; (void)encoding; (void)filetype;
    return NULL; /* "cannot open" - callers take their no-audio path */
}

static inline sox_format_t *sox_open_write(char const *path,
                                           sox_signalinfo_t const *signal,
                                           sox_encodinginfo_t const *encoding,
                                           char const *filetype,
                                           char const *ofilename,
                                           sox_bool (*overwrite_permitted)(void))
{
    (void)path; (void)signal; (void)encoding; (void)filetype;
    (void)ofilename; (void)overwrite_permitted;
    return NULL;
}

static inline int sox_close(sox_format_t *ft)
{
    (void)ft;
    return SOX_SUCCESS;
}

static inline size_t sox_read(sox_format_t *ft, sox_sample_t *buf, size_t len)
{
    (void)ft; (void)buf;
    return 0;
}

static inline size_t sox_write(sox_format_t *ft, sox_sample_t const *buf, size_t len)
{
    (void)ft; (void)buf;
    return len;
}

static inline sox_effects_chain_t *sox_create_effects_chain(sox_encoding_t const *in,
                                                             sox_encoding_t const *out)
{
    (void)in; (void)out;
    return NULL;
}

static inline void sox_delete_effects_chain(sox_effects_chain_t *chain)
{
    (void)chain;
}

static inline sox_effect_t *sox_create_effect(sox_effect_handler_t const *handler)
{
    (void)handler;
    return NULL;
}

static inline int sox_add_effect(sox_effects_chain_t *chain, sox_effect_t *effect,
                                 sox_signalinfo_t *in, sox_signalinfo_t *out)
{
    (void)chain; (void)effect; (void)in; (void)out;
    return SOX_SUCCESS;
}

static inline int sox_effect_options(sox_effect_t *effect, int argc, char **argv)
{
    (void)effect; (void)argc; (void)argv;
    return 0;
}

static inline sox_effect_handler_t const *sox_find_effect(char const *name)
{
    (void)name;
    return NULL;
}

static inline int sox_flow_effects(sox_effects_chain_t *chain,
                                   sox_flow_effects_callback *callback,
                                   void *client_data)
{
    (void)chain; (void)callback; (void)client_data;
    return SOX_SUCCESS;
}

#ifdef __cplusplus
}
#endif

#endif /* IMAGINATION_SOX_STUB_H */
"""


class ImaginationConan(ConanFile):
    name = "imagination"
    version = "3.6"
    description = "Imagination - lightweight GTK+3 DVD slideshow maker"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/imagination/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    # The application links nothing against itself; the pair is kept for
    # pipeline uniformity (l3afpad precedent).
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("imagination supports OHOS armv8 only")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # In-source build: intltool's po/ rules and the desktop merge cache
        # are not reliably VPATH-clean (l3afpad precedent).
        self.folders.build = "."

    def requirements(self):
        # PKG_CHECK_MODULES(PACKAGE, gtk+-3.0); the transition plugins
        # additionally check cairo >= 1.6 / glib-2.0 > 2.18.0, both of which
        # PkgConfigDeps emits transitively through the gtk graph.
        self.requires("gtk/3.24.43")

    def build_requirements(self):
        # AC_PROG_INTLTOOL wants intltool-update/merge/extract on PATH;
        # AM_GLIB_GNU_GETTEXT wants msgfmt/msgmerge/xgettext.
        self.tool_requires("intltool/0.51.0")
        self.tool_requires("gettext/0.22.5.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()

        # sox stub: satisfy the hard PKG_CHECK_MODULES(SOX) without a real
        # libsox (see recipe docstring). sox.pc lands directly in the
        # generators folder, which PkgConfigDeps already puts on
        # PKG_CONFIG_PATH - no env plumbing needed. The Cflags include path
        # is absolute, exactly like the pc files PkgConfigDeps itself emits.
        stub_root = os.path.join(self.generators_folder, "sox-stub")
        stub_inc = os.path.join(stub_root, "include")
        os.makedirs(stub_inc, exist_ok=True)
        save(self, os.path.join(stub_inc, "sox.h"), _SOX_STUB_H)
        save(self, os.path.join(self.generators_folder, "sox.pc"),
             _SOX_STUB_PC.format(include_dir=stub_inc))
        self.output.info(f"sox no-op stub generated under {stub_root}")

        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # configure's conftest link/run steps are unreliable in the sandbox
        # (l3afpad/intltool precedents).
        tc.configure_args.extend([
            "ac_cv_prog_cc_works=yes",
            "ac_cv_prog_cc_cross=yes",
        ])
        tc.generate()

    def _extra_link_libs(self):
        """-lgmodule-2.0 and -lintl plus glib's libdir, for the final link.

        imagination_LDADD hardcodes -lgmodule-2.0, and glib's gi18n.h maps
        gettext() onto g_libintl_* aliases that live in glib's private
        libintl; glib's .pc files propagate neither. The flags ride on
        make's own LIBS variable (appended after $(imagination_LDADD)),
        NOT on configure - an unconditional -l in LIBS at configure time
        breaks AC_PROG_CC's conftest (l3afpad _intl_link_flags precedent).
        """
        flags = ["-lgmodule-2.0", "-lintl"]
        if "glib" in self.dependencies:
            for libdir in self.dependencies["glib"].cpp_info.libdirs:
                flags.append(f'-L"{libdir}"')
        return " ".join(flags)

    def _replace_config_scripts(self):
        """Self-contained OHOS-aware config.guess/config.sub (aris/2.2).

        The 2020-01 scripts shipped in the tarball cannot recognise
        HarmonyOS ("unable to guess system type").
        """
        guess = (
            "#!/bin/sh\n"
            "# OHOS-aware config.guess (self-contained)\n"
            "machine=$(uname -m 2>/dev/null || echo unknown)\n"
            "system=$(uname -s 2>/dev/null || echo unknown)\n"
            'case "$system" in\n'
            "    HarmonyOS|OHOS)\n"
            '        echo "${machine}-unknown-linux-ohos"\n'
            "        ;;\n"
            "    *)\n"
            '        echo "${machine}-unknown-linux-gnu"\n'
            "        ;;\n"
            "esac\n"
            "exit 0\n"
        )
        sub = (
            "#!/bin/sh\n"
            "# OHOS-aware config.sub (self-contained)\n"
            "# Always pass through the input triplet\n"
            'if [ $# -eq 0 ] || [ -z "$1" ]; then\n'
            '    echo "aarch64-unknown-linux-ohos"\n'
            "    exit 0\n"
            "fi\n"
            'echo "$1"\n'
            "exit 0\n"
        )
        for name, text in (("config.guess", guess), ("config.sub", sub)):
            path = os.path.join(self.source_folder, name)
            if os.path.isfile(path):
                save(self, path, text)
                os.chmod(path, 0o755)
                self.output.info(f"replaced {name} with OHOS-aware version")

    def _intltoolize_shim_dir(self):
        """Dir holding a patched ``intltoolize`` with the right data prefix.

        The conan intltool package's intltoolize script bakes ``prefix=/``
        (only MINGW32 derives it from $0), so a plain PATH exec would look
        under ``//share/intltool`` and die with "cannot copy".  Copy the
        script and rewrite that one constant to the intltool package folder
        (l3afpad/0.8.18.1.11 and ddccontrol/1.0.3 shim precedent), which
        makes pkgdatadir=<pkg>/share/intltool and
        aclocaldir=<pkg>/share/aclocal correct.  Idempotent.
        """
        intltool_bin = None
        intltool_root = None
        for dep in self.dependencies.build.values():
            if dep.ref.name != "intltool":
                continue
            root = dep.package_folder or ""
            cand = os.path.join(root, "bin", "intltoolize")
            if os.path.isfile(cand):
                intltool_bin = cand
                intltool_root = root
        if not intltool_bin:
            raise ConanException("intltoolize not found in the intltool package")
        shim_dir = os.path.join(self.build_folder, "toolshim")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "intltoolize")
        with open(intltool_bin, encoding="utf-8", errors="surrogateescape") as fh:
            text = fh.read()
        if not re.search(r"^prefix=/", text, flags=re.M):
            raise ConanException(
                "unexpected intltoolize layout: no 'prefix=/' constant to rewrite")
        text = re.sub(r"^prefix=/", "prefix=%s" % intltool_root, text,
                      count=1, flags=re.M)
        with open(shim, "w", encoding="utf-8", errors="surrogateescape") as fh:
            fh.write(text)
        os.chmod(shim, 0o755)
        self.output.info("intltoolize shim prefix -> %s" % intltool_root)
        return shim_dir

    def _run_intltoolize(self):
        """Force-refresh po/Makefile.in.in + intltool.m4 from intltool/0.51.0.

        CI #92619 (worker CI-035) failed in config.status' po/stamp-it
        block with "po/Makefile.in.in was not created by intltoolize".
        The guard greps the REGENERATED po/Makefile.in for the
        "# INTLTOOL_MAKEFILE" marker; the 2018 tarball ships a
        pre-generated po/Makefile.in WITHOUT that marker, and when the
        worker's fork-pressure storm ("fork: retry: Resource temporarily
        unavailable" all over the log) upsets config.status' po/Makefile.in
        regeneration step, the stale marker-less copy survives and the
        guard trips.  Two-part fix before configure: (1) intltoolize
        --force --copy re-seals po/Makefile.in.in from the intltool/0.51.0
        package (template carries the marker; also re-touches
        the 0-byte intltool-*.in placeholders referenced from Makefile.am -
        activity-log 0.9.7 / libgnomecanvas 2.30.3 / l3afpad 0.8.18.1.11
        intltoolize precedents); (2) remove the stale pre-generated po/Makefile.in +
        po/Makefile + po/stamp-it so config.status must recreate them
        fresh from the sealed Makefile.in.in (ac_config_files includes
        po/Makefile.in - regeneration with the marker verified locally,
        twice).  Idempotent and network-free.
        """
        shim_dir = self._intltoolize_shim_dir()
        self.run('PATH="%s:$PATH" intltoolize --force --copy' % shim_dir,
                 cwd=self.source_folder, env="conanbuild")
        for stale in ("po/Makefile.in", "po/Makefile", "po/stamp-it"):
            path = os.path.join(self.source_folder, stale)
            if os.path.isfile(path):
                os.remove(path)
                self.output.info("removed stale pre-generated %s" % stale)
        marker = os.path.join(self.source_folder, "po", "Makefile.in.in")
        with open(marker, encoding="utf-8", errors="surrogateescape") as fh:
            if "INTLTOOL_MAKEFILE" not in fh.read():
                raise ConanException("intltoolize left po/Makefile.in.in without marker")

    def build(self):
        apply_conandata_patches(self)
        self._replace_config_scripts()
        self._run_intltoolize()
        autotools = Autotools(self)
        autotools.configure()
        # -j1: the hmdfs jobserver fifo raises EPERM (l3afpad precedent).
        # LIBS must be ONE shell word (l3afpad precedent).
        autotools.make(args=["-j1", 'LIBS="%s"' % self._extra_link_libs()])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

    def package_info(self):
        # bin/imagination + lib/imagination/*.so (GModule transition
        # plugins, resolved by absolute path at runtime) + share/ data.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.libs = []
