#!/usr/bin/env python3
"""Conan recipe for libircclient 1.10 on HarmonyOS PC (OHOS / aarch64).

libircclient is a small LGPL IRC client library: it owns the socket, the IRC
protocol state machine, DCC transfers and the event dispatch loop, and leaves
the UI entirely to the caller.  Single translation unit upstream
(`src/libircclient.c` #includes the other .c files), so the whole library is
one object file plus the public headers.

Upstream: https://sourceforge.net/projects/libircclient/  (LGPL-3.0-or-later)

--------------------------------------------------------------------------
Why this recipe looks the way it does
--------------------------------------------------------------------------
1. The tarball ships a pre-generated ./configure (autoconf 2.5x era), so it is
   used as-is; the recipe never runs autoreconf.

2. The build has to run **inside the source tree**.  `src/Makefile.in` reaches
   the headers through the relative path `-I../include`, and configure writes
   the generated `src/config.h` next to portable.c, which includes it as
   `"config.h"`.  An out-of-tree build (conan's default `build-release`
   subfolder) breaks both, so `self.folders.build` is emptied and everything
   happens at the top of the unpacked tree.

3. `make` at the top of the tree also descends into `examples/`, which needs a
   terminal and, for its SSL sample, a full OpenSSL.  Those are demo programs,
   not part of the library, so the recipe builds `-C src` only.

4. The upstream `install` target cannot be used: it unconditionally copies
   `libircclient.so` (so a static-only build fails on a missing file), it
   never installs `libircclient.a`, and it hardcodes an unversioned .so name.
   Headers and artifacts are therefore copied explicitly in `package()`.

5. `gethostbyname_r` / `inet_ntoa` have no declaration unless a feature-test
   macro asks for it; musl-based OHOS headers behave the same way glibc does
   here.  `-D_GNU_SOURCE` is injected through CFLAGS.  configure only *appends*
   to CFLAGS (`CFLAGS="${CFLAGS} -O3"`), so the flag survives.

6. `--enable-threads` is upstream's default (it adds `-DENABLE_THREADS
   -D_REENTRANT`).  OHOS keeps the pthread entry points in libc, so no extra
   link flag is required and none is added.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibircclientConan(ConanFile):
    name = "libircclient"
    version = "1.10"
    description = ("IRC client library: protocol state machine, DCC file "
                   "transfer and event dispatch, UI-agnostic")
    license = "LGPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/libircclient/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("irc", "chat", "network", "tcp", "library")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"

    options = {"shared": [True, False], "fPIC": [True, False]}
    # Static by default: this is a system-name library, and a static archive
    # needs neither a SONAME nor an OHOS code signature to be usable.
    default_options = {"shared": False, "fPIC": True}

    exports_sources = ("conandata.yml", "manifest.yaml", "notes.md")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if not self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)
        # In-source build: see note 2 above.
        self.folders.build = ""

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # See note 5 above.  gnu99 keeps the 2018 sources away from the C23
        # default of newer clang releases.
        tc.extra_cflags = list(tc.extra_cflags or []) + ["-D_GNU_SOURCE", "-std=gnu99"]
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
        else:
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--enable-threads")
        tc.generate()

    def build(self):
        # config.status is emitted from a heredoc inside configure, so patching
        # the template repairs the generated script too.  Both occurrences
        # create the private temporary directory with umask 077, i.e. mode
        # 0700, and OHOS then refuses the very same process when it writes the
        # awk helper in there:
        #   can't create ./confXXXXXX/subs1.awk: Permission denied
        # 0775 is enough isolation for a build tree.  Patched here rather than
        # in source() so it also applies when the source cache is reused.
        replace_in_file(self, os.path.join(self.build_folder, "configure"),
                        "umask 077", "umask 002", strict=True)
        # The Autotools helper execs ./configure directly, which OHOS rejects
        # with EACCES (Error 126) even though the file is mode 0755 -- the same
        # behaviour already documented for other autotools recipes in this
        # repository.  Launching it through sh bypasses the exec check without
        # changing the script itself.
        toolchain = AutotoolsToolchain(self)
        toolchain.extra_cflags = list(toolchain.extra_cflags or []) + [
            "-D_GNU_SOURCE", "-std=gnu99"
        ]
        cflags = list(toolchain.cflags) + list(toolchain.extra_cflags)
        # The toolchain keeps -D macros in a separate attribute; configure has
        # no CPPFLAGS default here, so fold them into CFLAGS.
        flags = " ".join(["-D%s" % d for d in toolchain.defines] + cflags)
        # --prefix points at the build folder: nothing is installed here, the
        # package() method copies artefacts by hand (see note 4).
        args = [
            "--prefix=%s" % self.build_folder,
            "--enable-threads",
            "--enable-shared" if self.options.shared else "--disable-shared",
        ]
        env = 'CFLAGS="%s" LDFLAGS="%s" ' % (
            flags,
            " ".join(toolchain.ldflags),
        )
        self.run(env + "sh ./configure " + " ".join(args), cwd=self.build_folder)
        # -C src: the library only; examples/ are demos (see note 3 above).
        autotools = Autotools(self)
        autotools.make(args=["-C", "src"])

    def _sign_ohos_elf(self, path):
        """Self-sign a shared object so the OHOS XPM loader will map it."""
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        temporary = path + ".libircclient-signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", temporary,
             "-selfSign", "1"], check=True, timeout=60
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary], check=True, capture_output=True,
            text=True, timeout=30
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed shared object has invalid .codesign count")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)

    def package(self):
        # See note 4 above: headers and artifacts are copied by hand.
        copy(self, "*.h",
             src=os.path.join(self.build_folder, "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)
        copy(self, "LICENSE",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

        library = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            # The Makefile links with `-Wl,-soname,libircclient.so.1` but writes
            # the file as plain `libircclient.so`; the archive is stored under
            # the SONAME with the usual unversioned symlink next to it.
            copy(self, "libircclient.so",
                 src=os.path.join(self.build_folder, "src"),
                 dst=library, keep_path=False)
            entity = os.path.join(library, "libircclient.so.1")
            os.replace(os.path.join(library, "libircclient.so"), entity)
            os.symlink("libircclient.so.1", os.path.join(library, "libircclient.so"))
            if str(self.settings.os) == "OHOS":
                self._sign_ohos_elf(entity)
        else:
            copy(self, "libircclient.a",
                 src=os.path.join(self.build_folder, "src"),
                 dst=library, keep_path=False)

        # The tarball ships man/libircclient.1 (it is a section 1 page even
        # though it documents a library).
        copy(self, "*.1", src=os.path.join(self.build_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)

    def package_info(self):
        # Conan consumer logic prepends "lib"/suffix itself, so the entry must
        # be the bare stem: "ircclient" resolves to lib/libircclient.a.
        self.cpp_info.libs = ["ircclient"]
        # Upstream compiles with -DENABLE_THREADS by default; consumers of a
        # static archive must see the same macro, otherwise the session
        # structure layout differs between library and callers.  No pthread
        # link flag is added on purpose: on OHOS the pthread entry points live
        # in libc and there is no separate libpthread to link against.
        self.cpp_info.defines = ["ENABLE_THREADS", "_REENTRANT"]
