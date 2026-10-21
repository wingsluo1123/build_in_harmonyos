from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, copy, get, rm, rmdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from shlex import quote
import os
import shutil


class LamConan(ConanFile):
    name = "lam"
    version = "7.1.4"
    description = "LAM/MPI: a portable Message Passing Interface implementation for parallel and distributed computing"
    license = "LAM/MPI"
    homepage = "https://www.lam-mpi.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _propagate_config_ohos(self):
        # The 2005 tarball ships 23 byte-identical copies of config.guess and
        # config.sub (one per SSI/boot module configure).  The conandata patches
        # only touch the canonical config/ pair; replicate the patched files
        # over the other copies so every sub-configure understands the
        # aarch64-linux-ohos triplet.
        source_folder = self.source_folder
        canonical_guess = os.path.join(source_folder, "config", "config.guess")
        canonical_sub = os.path.join(source_folder, "config", "config.sub")
        for root, _, files in os.walk(source_folder):
            for filename in files:
                if filename not in ("config.guess", "config.sub"):
                    continue
                path = os.path.join(root, filename)
                if os.path.samefile(path, canonical_guess) or os.path.samefile(path, canonical_sub):
                    continue
                canonical = canonical_guess if filename == "config.guess" else canonical_sub
                with open(canonical, "rb") as src:
                    content = src.read()
                with open(path, "wb") as dst:
                    dst.write(content)

    def _propagate_confstat_umask(self):
        # Every configure script in the tarball creates its config.status
        # tmp dir with "umask 077", i.e. mode 0700.  On the CI worker the
        # conan cache lives on a filesystem (HMDFS) where a newly created
        # 0700-mode directory rejects file creation ("can't create
        # .../subs.sed: Permission denied"), leaving Makefiles truncated
        # or absent.  The stanza exists in TWO per-script copies (mktemp
        # line + mkdir fallback) and TWO autoconf dialects:
        #   * autoconf 2.59 (top-level + SSI/boot/totalview scripts):
        #       (umask 077 && mktemp -d -q "./confstatXXXXXX")
        #       (umask 077 && mkdir $tmp)                       [fallback]
        #   * autoconf 2.59c (share/libltdl/configure only):
        #       (umask 077 && mktemp -d -q "./confXXXXXX")
        #       (umask 077 && mkdir "$tmp")                     [fallback]
        # CI build #89213 proved the first form's mktemp line alone is not
        # enough: with only it rewritten to umask 000, configure and
        # share/mpi built fine, but libltdl (2.59c, stanza untouched) died
        # with "No rule to make target 'all'" -- its config.status could
        # not write a Makefile.  Rewrite ALL four shapes to umask 000
        # (same fix as autodir/0.99.9, already merged in this repo).
        # A patch file cannot do this reliably: stanza positions drift
        # across 45k-line generated scripts, so a positional hunk fails
        # to apply.  Done programmatically instead, at byte level to be
        # encoding-safe (the 2.59c script is never re-encoded here).
        source_folder = self.source_folder
        patterns = [
            (b'(umask 077 && mktemp -d -q "./confstatXXXXXX")',
             b'(umask 000 && mktemp -d -q "./confstatXXXXXX")'),
            (b'(umask 077 && mktemp -d -q "./confXXXXXX")',
             b'(umask 000 && mktemp -d -q "./confXXXXXX")'),
            (b'(umask 077 && mkdir $tmp)',
             b'(umask 000 && mkdir $tmp)'),
            (b'(umask 077 && mkdir "$tmp")',
             b'(umask 000 && mkdir "$tmp")'),
        ]
        for root, _, files in os.walk(source_folder):
            for filename in files:
                if not filename.endswith("configure"):
                    continue
                path = os.path.join(root, filename)
                try:
                    with open(path, "rb") as f:
                        content = f.read()
                except OSError:
                    continue
                new_content = content
                for old, new in patterns:
                    new_content = new_content.replace(old, new)
                if new_content != content:
                    with open(path, "wb") as f:
                        f.write(new_content)

    def _configure_args(self):
        args = [
            "--prefix=/",
            "--without-romio",
            "--without-fc",
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--enable-static" if not self.options.shared else "--disable-static",
            # The conan cache lives on a filesystem where a script whose
            # shebang points at the CONFIG_SHELL bash cannot be exec'd
            # ("bad interpreter: Permission denied").  libtool.m4 generates
            # the libtool script with "#! $SHELL", and SHELL defaults to
            # $CONFIG_SHELL from the profile buildenv.  Pinning SHELL=/bin/sh
            # keeps every generated libtool/config.status shebang exec-safe
            # (the POSIX configure scripts run fine under /bin/sh, and the
            # mpich-style explicit bash invocation still drives configure).
            "SHELL=/bin/sh",
        ]
        if self.options.fPIC:
            args.extend(["CFLAGS=-O2 -fPIC", "CXXFLAGS=-O2 -fPIC"])
        if self.settings.os == "OHOS":
            # The 2007-era config.sub cannot parse default uname output from
            # HarmonyOS.  The explicit linux-ohos triplets work together with
            # 0002-config-guess-ohos.patch and 0003-config-sub-ohos.patch.
            args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        return args

    def generate(self):
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "lam/7.1.4 currently supports only OHOS armv8"
            )
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._propagate_config_ohos()
        self._propagate_confstat_umask()

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        # The cache filesystem intermittently denies stat() on files inside
        # long-lived process trees, which makes the rsh boot module's
        # configure-time search for a remote shell fail ("checking for
        # ssh... no") even though /usr/bin/ssh exists.  Pre-setting
        # RSH_COMMAND is that module configure's documented override: with
        # it set the whole search is skipped ("Ignored - already set") and
        # the LAM_SSI_BOOT_RSH_RSH macro is defined to the given value.
        # Note RSH_FULL_PATH does NOT work here -- that module's configure
        # unconditionally resets it before its own search.
        os.environ["RSH_COMMAND"] = "/usr/bin/ssh"

        # The conan cache lives on a filesystem that does not preserve the
        # executable bit, so Autotools.configure()'s direct execution of
        # ./configure fails with "Permission denied" (error 126).  Invoke the
        # script through an explicit shell, as the mpich recipe does.
        bash = shutil.which("bash") or shutil.which("sh") or "/system/bin/sh"
        configure = os.path.join(self.source_folder, "configure")
        args = " ".join(quote(arg) for arg in self._configure_args())
        self.run(f"{quote(bash)} {quote(configure)} {args}")

        # The cache filesystem does not support symbolic links, so configure
        # detects "ln -s ... no, using cp -p" (LN_S).  Two generated Makefiles
        # then misbehave, because "cp" needs its source to exist while "ln -s"
        # does not:
        #  - share/pmpi/Makefile stub rules hard-code "ln -s" instead of
        #    $(LN_S); rewriting them to "cp -p" is equivalent for compilation.
        #  - tools/wrappers/Makefile's install-exec-hook creates hcp from
        #    mpiCC before mpiCC itself is created (from mpic++) a few lines
        #    later.  Create hcp directly from mpic++ (same content; this also
        #    matches the alternative hook upstream keeps commented out).
        for rel, replacements in (
            (("share", "pmpi", "Makefile"), [
                ("ln -s $(top_srcdir)/share/mpi/",
                 "cp -p $(top_srcdir)/share/mpi/"),
            ]),
            (("tools", "wrappers", "Makefile"), [
                ("$(LN_S) mpiCC$(EXEEXT) hcp$(EXEEXT)",
                 "$(LN_S) mpic++$(EXEEXT) hcp$(EXEEXT)"),
            ]),
        ):
            makefile = os.path.join(self.build_folder, *rel)
            if os.path.exists(makefile):
                with open(makefile) as f:
                    content = f.read()
                for old, new in replacements:
                    content = content.replace(old, new)
                with open(makefile, "w") as f:
                    f.write(content)

        # Parallel make.  The previous serial invocation carried a comment
        # claiming "~25 min, well within the default CI timeout"; the real
        # measurement is 56m47s -- a ~3 min margin against CI's 3600s cap,
        # and CI build #92967 timed out (its worker was shedding fork EAGAIN
        # storms, which slow every sub-process spawn and can also corrupt
        # sub-configure probe results).  GNU make >= 4.2 builds the -j
        # jobserver on an anonymous pipe(2), not a FIFO, so the conan-cache
        # filesystem's mkfifo refusal does not apply: verified live with
        # make 4.4.1 on the HMDFS cache (jobserver comes up cleanly, RC=0),
        # and in-repo precedent (openblas/0.3.33, c-algorithms/1.2.0) builds
        # through CI with make -j20.  Cap at 8 to keep fork pressure modest
        # on contended workers while still cutting the compile phase ~5x.
        self.run(f"make -j{min(os.cpu_count() or 1, 8)}")

    def package(self):
        Autotools(self).install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        for pattern in ("*.la", "*.dylib"):
            rm(self, pattern, folder=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["lammpi++", "mpi", "lam"]
        self.cpp_info.system_libs = ["dl"]
        self.cpp_info.defines = ["_REENTRANT"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "LAM")
        self.cpp_info.set_property("cmake_target_name", "LAM::LAM")
        self.cpp_info.set_property("pkg_config_name", "lam")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        # LAM tools look up their help file under $LAMHOME/etc and
        # $SYSCONFDIR (compiled in as /etc because of the DESTDIR-style
        # prefix); point LAMHELPDIR at the packaged copy instead.
        etcdir = os.path.join(self.package_folder, "etc")
        self.runenv_info.prepend_path("LAMHELPDIR", etcdir)
        self.buildenv_info.prepend_path("LAMHELPDIR", etcdir)
        # hboot resolves the lamd process schema (lam-conf.lamd), lamboot
        # resolves the boot hostfile (lam-bhost.def) under $LAMHOME/etc
        # before falling back to $SYSCONFDIR (/etc, absent for a DESTDIR
        # install).  LAMHOME makes every tool resolve etc/ files from the
        # package regardless of the install prefix.
        self.runenv_info.define("LAMHOME", self.package_folder)
        self.buildenv_info.define("LAMHOME", self.package_folder)
