#!/usr/bin/env python3
"""Conan recipe — imap 2007f (custom UW Makefile, c-client library)."""

import os
import shutil
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import download, check_sha256, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


required_conan_version = ">=2.0"


class ImapConan(ConanFile):
    name = "imap"
    version = "2007f"
    description = "University of Washington IMAP toolkit with c-client library and IMAP/POP servers"
    license = "Apache-2.0"
    homepage = "https://www.washington.edu/imap/"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "imap only supports Linux/OHOS, not %s" % str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def _download_first_ok(self, entry, filename):
        # Pure-Python download (urllib, no external curl/tar exec) trying
        # each mirror URL in order. conandata URLs/sha256 unchanged.
        urls = entry.get("url", [])
        if isinstance(urls, str):
            urls = [urls]
        sha256 = entry.get("sha256", "")
        last_err = None
        for url in urls:
            try:
                self.output.info("imap download trying: %s" % url)
                download(self, url, filename)
                base = getattr(self, "base_source_folder", None) or self.source_folder
                local = os.path.join(base, filename)
                if not os.path.isfile(local):
                    for cand in (os.path.join(self.source_folder, filename),
                                 os.path.join(os.getcwd(), filename),
                                 filename):
                        if os.path.isfile(cand):
                            local = cand
                            break
                if sha256:
                    check_sha256(self, local, sha256)
                self.output.info("imap download ok: %s (%d bytes)" % (url, os.path.getsize(local)))
                return local
            except Exception as e:
                self.output.warning("imap download failed %s: %s" % (url, e))
                last_err = e
                continue
        raise ConanException("imap download failed for all mirrors %s: %s" % (urls, last_err))

    @staticmethod
    def _extract_tar_gz_noexec(tar_path, dest_dir, strip_root=True):
        # Extract .tar.gz with stdlib tarfile only (never exec host tar).
        # True-device 2026-10-16 reports
        # `sh: /storage/Users/currentUser/.harmonybrew/bin/tar: Operation not
        # permitted` in compile phase; this recipe never calls tar, so the
        # only tar dependency was Conan automatic unpacking (svox/1.0 same
        # signature precedent). strip_root mirrors get(strip_root=True).
        os.makedirs(dest_dir, exist_ok=True)
        with tarfile.open(tar_path, "r:gz") as tf:
            members = tf.getmembers()
            root = ""
            if strip_root and members:
                tops = sorted(set(m.name.split("/")[0] for m in members if m.name))
                if len(tops) == 1 and any("/" in m.name for m in members):
                    root = tops[0] + "/"
            for m in members:
                name = m.name
                if root:
                    if name == root.rstrip("/"):
                        continue
                    if name.startswith(root):
                        name = name[len(root):]
                        if not name:
                            continue
                        m.name = name
                tf.extract(m, path=dest_dir)

    def source(self):
        # Pure-Python fetch+extract: never exec host tar (harmonybrew tar may
        # be EPERM on some runners). conandata URLs/sha256 unchanged.
        tgz = self._download_first_ok(self.conan_data["sources"], "imap-2007f.tar.gz")
        self._extract_tar_gz_noexec(tgz, self.source_folder, strip_root=True)
        try:
            os.remove(tgz)
        except OSError:
            pass
        for stray in ("imap-2007f.tar.gz",):
            for base in dict.fromkeys([self.source_folder, os.getcwd()]):
                p = os.path.join(base, stray)
                if os.path.isfile(p) and os.path.abspath(p) != os.path.abspath(tgz):
                    try:
                        os.remove(p)
                    except OSError:
                        pass

    def _exec_ok(self, cand):
        # Single lightweight executability probe (one `--version` run).
        # Returns True only if the candidate really executes in this
        # sandbox; any spawn failure / non-zero exit means unusable.
        try:
            r = subprocess.run(
                [cand, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
            )
            return r.returncode == 0
        except Exception:
            return False

    def _usable_tool(self, conf_key, fallbacks):
        # make itself is fine as an HMBS absolute path (the top-level make
        # already runs from /storage/.../usr/local/bin/make), so keep the
        # cheap resolution for non-compiler tools.
        if conf_key != "c":
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            cand = compilers.get(conf_key)
            if cand and os.path.isabs(str(cand)) and str(cand).strip():
                return str(cand)
            for name in fallbacks:
                found = shutil.which(name)
                if found and os.path.isfile(found):
                    return found
            hmbs_conf = {"make": "user.hmbs:make_path"}.get(conf_key)
            if hmbs_conf:
                hmbs_val = self.conf.get(hmbs_conf)
                if hmbs_val and os.path.isabs(str(hmbs_val)):
                    return str(hmbs_val)
            if cand:
                return str(cand)
            return fallbacks[0]
        # C compiler: the preflight sandbox blocks exec of the profile's
        # absolute toolchain path (/data/service/hnp/bin/clang:
        # "inaccessible or not found" from /bin/sh in the c-client
        # sub-make, and os.path.isfile was already False for it in the
        # recipe context). Neither blind PATH fallback (round 1) nor
        # blind trust of the conf absolute path (round 2) works, so
        # verify by execution: conf candidate first, then PATH-resolved
        # names, first `--version`-clean candidate wins, stop at once.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        conf_c = compilers.get("c")
        seen = set()
        ordered = []
        for cand in [conf_c] + fallbacks:
            if not cand:
                continue
            cand = str(cand)
            if cand in seen:
                continue
            seen.add(cand)
            ordered.append(cand)
        for cand in ordered:
            probe = cand
            if not os.path.isabs(cand):
                resolved = shutil.which(cand)
                if not resolved:
                    self.output.info("CC probe: %s not on PATH, skip" % cand)
                    continue
                probe = resolved
            if self._exec_ok(probe):
                self.output.info("CC probe: using working compiler %s" % probe)
                return probe
            self.output.info("CC probe: %s not executable, skip" % probe)
        self.output.warning("CC probe: no candidate executed; falling back to profile value")
        if conf_c:
            return str(conf_c)
        return fallbacks[0]

    def _probe_host_tar(self):
        # Non-fatal evidence probe for the broken host tar (next-round triage).
        # Never fails the build; only logs which tar binaries exist and whether
        # they exec. Recipe extraction/build never calls tar (pure-Python
        # tarfile + CC/make only), so a broken harmonybrew tar must not break
        # the build.
        try:
            cands = []
            w = shutil.which("tar")
            if w:
                cands.append(w)
            for p in ("/bin/tar", "/usr/bin/tar",
                      "/storage/Users/currentUser/.harmonybrew/bin/tar"):
                if p not in cands:
                    cands.append(p)
            for p in cands:
                exists = os.path.isfile(p)
                x_ok = os.access(p, os.X_OK) if exists else False
                run = "skipped"
                if exists:
                    try:
                        r = subprocess.run([p, "--version"], capture_output=True,
                                           timeout=10)
                        out = ((r.stdout or b"") + (r.stderr or b"")).decode(
                            "utf-8", errors="ignore").strip().splitlines()
                        run = "rc=%d %s" % (r.returncode, (out[0][:120] if out else ""))
                    except Exception as e:
                        run = "exec-failed: %s" % str(e)[:160]
                self.output.info("HOST_TAR_PROBE path=%s exists=%s x_ok=%s run=%s"
                                 % (p, exists, x_ok, run))
            self.output.info("HOST_TAR_PROBE recipe uses pure-Python tarfile only; host tar status is informational")
        except Exception as e:
            self.output.warning("HOST_TAR_PROBE failed: %s" % e)

    def build(self):
        self._probe_host_tar()
        apply_conandata_patches(self)
        cc = self._usable_tool("c", ["clang", "cc", "gcc"])
        make = self._usable_tool("make", ["make", "gmake"])
        # UW IMAP only supports in-source builds: its top-level Makefile
        # creates symlinked trees (c-client/, mtest/, imapd/, ...) via
        # tools/an and drives sub-makes with relative paths. Running
        # `make` in build_folder (basic_layout out-of-source) finds no
        # Makefile with the port target -> "No rule to make target".
        # Always run in source_folder where the authentic Makefile lives.
        # Port selection: lnx (non-shadow) instead of slx (Secure Linux).
        # The slx OS layer (src/osdep/unix/os_slx.c) and its CHECKPW=psx
        # module call getspnam/endspent from shadow.h, which OHOS does not
        # provide (undeclared -> int-conversion hard error in osdep.o).
        # The lnx OS layer (os_lnx.c) has no shadow/crypt/pam references.
        # PASSWDTYPE=nul selects ckp_nul.c (checkpw always returns NIL,
        # server-side only; the packaged c-client client API is
        # unaffected) and also skips the interactive lnxok prompt via the
        # lnxnul rule. SSLTYPE=none avoids the OpenSSL 0.9/1.0-only
        # ssl_unix.c code and selects the `sslnone` target which asks an
        # interactive "Type y or n" confirmation; preflight is
        # non-interactive, so feed `y` on stdin defensively.
        # EXTRACFLAGS carries PIC + OHOS-safe flags into every sub-make.
        src = self.source_folder
        mk = os.path.join(src, "Makefile")
        if not os.path.isfile(mk):
            self.output.warning("top-level Makefile not at %s; listing source_folder:" % src)
            try:
                self.output.info("source_folder entries: %s" % sorted(os.listdir(src))[:50])
            except OSError as e:
                self.output.warning("cannot list source_folder: %s" % e)
            raise ConanInvalidConfiguration("UW IMAP top-level Makefile not found in source_folder")
        self.output.info("building c-client only in source_folder: %s" % src)
        # c-client-only scope: top-level `lnx` runs `build: OSTYPE rebuild bundled`;
        # `bundled` compiles interactive mtest + imapd/ipopd/mailutil servers which
        # are NOT packaged (servers need inetd/mail spool/PAM; notes.md documents
        # out-of-scope). mtest mm_login() calls obsolete getpass(3)
        # (`strcpy (pwd,getpass (s))`); OHOS sysroot no longer declares getpass so
        # clang fails mtest.o with `incompatible integer to pointer conversion`
        # (true-device 2026-10-16). Same c-client/c-client.a without unshipped tools:
        # `an` sets up the symlinked trees, then OSTYPE/rebuild with BUILDTYPE=lnx.
        self.run("\"%s\" clean -j1" % make, cwd=src)
        self.run(
            "for i in 1 2 3 4 5 6 7 8; do echo y; done | \"%s\" an SSLTYPE=none -j1" % make,
            cwd=src,
        )
        self.run(
            "\"%s\" OSTYPE rebuild rebuildclean BUILDTYPE=lnx PASSWDTYPE=nul SSLTYPE=none IP=4 EXTRADRIVERS=mbox EXTRAAUTHENTICATORS= CC=\"%s\" EXTRACFLAGS=\"-fPIC -O2\" MAKE=\"%s\" -j1" % (make, cc, make),
            cwd=src,
        )

    def package(self):
        # Artifacts are produced by the in-source build in source_folder,
        # but conan may also copy sources to build_folder: search every
        # plausible location (source_folder, build_folder and its
        # build-release subdir) instead of assuming one fixed path.
        search_roots = [self.source_folder]
        try:
            if self.build_folder and self.build_folder != self.source_folder:
                search_roots.append(self.build_folder)
                search_roots.append(os.path.join(self.build_folder, "build-release"))
        except Exception:
            pass
        lib_built = None
        for root in search_roots:
            for p in (
                os.path.join(root, "c-client", "c-client.a"),
                os.path.join(root, "c-client.a"),
            ):
                if os.path.isfile(p):
                    lib_built = p
                    break
            if lib_built:
                break
        if lib_built is None:
            raise ConanInvalidConfiguration("c-client.a not found after make lnx")
        lib_dir = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        shutil.copy2(lib_built, os.path.join(lib_dir, "libc-client.a"))
        inc_dir = os.path.join(self.package_folder, "include")
        os.makedirs(inc_dir, exist_ok=True)
        built_root = os.path.dirname(os.path.dirname(lib_built))
        for hdr_root in (
            os.path.join(built_root, "c-client"),
            os.path.join(self.source_folder, "c-client"),
            os.path.join(self.source_folder, "src", "c-client"),
        ):
            if os.path.isdir(hdr_root):
                copy(self, "*.h", src=hdr_root, dst=inc_dir, keep_path=False)
        for lic_root in (built_root, self.source_folder):
            copy(self, "LICENSE.txt", src=lic_root, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
            copy(self, "LICENSE", src=lic_root, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["c-client"]
